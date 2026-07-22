from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from productos.models import Descuento, Producto
from productos.serializers import ProductoListSerializer
from .models import Boleta, DetalleBoleta, CarritoPersistente, ItemCarrito

class DetalleBoletaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = DetalleBoleta
        fields = (
            'id', 'producto', 'producto_nombre', 'producto_sku', 'imagen_url',
            'cantidad', 'precio_unitario', 'descuento_aplicado', 'subtotal',
        )

    def get_imagen_url(self, obj):
        producto = obj.producto
        request = self.context.get('request')
        if producto.imagen_principal:
            url = producto.imagen_principal.url
            return request.build_absolute_uri(url) if request else url
        foto = producto.fotos.order_by('orden', 'creado').first()
        if foto and foto.imagen:
            url = foto.imagen.url
            return request.build_absolute_uri(url) if request else url
        return None

class BoletaListSerializer(serializers.ModelSerializer):
    cliente_email = serializers.EmailField(source='cliente.email', read_only=True, default=None)
    vendedor_email = serializers.EmailField(source='vendedor.email', read_only=True, default=None)

    class Meta:
        model = Boleta
        fields = (
            'id', 'numero', 'tipo', 'estado', 'fecha',
            'total', 'cliente_email', 'vendedor_email', 'pdf_url',
        )

class BoletaDetailSerializer(serializers.ModelSerializer):
    detalles = DetalleBoletaSerializer(many=True, read_only=True)
    cliente_email = serializers.EmailField(source='cliente.email', read_only=True, default=None)
    vendedor_email = serializers.EmailField(source='vendedor.email', read_only=True, default=None)

    class Meta:
        model = Boleta
        fields = (
            'id', 'numero', 'tipo', 'estado', 'fecha',
            'subtotal', 'igv', 'descuento_global', 'total',
            'cliente', 'cliente_email',
            'vendedor', 'vendedor_email',
            'turno',
            'anulada_fecha', 'anulada_motivo',
            'pdf_url', 'detalles',
        )

class ItemBoletaInputSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50)
    cantidad = serializers.IntegerField(min_value=1)

class BoletaCreateSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(
        choices=Boleta.Tipo.choices, default=Boleta.Tipo.BOLETA,
    )
    cliente = serializers.IntegerField(required=False, allow_null=True)
    descuento_global = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        min_value=Decimal('0.00'), default=Decimal('0.00'),
    )
    items = ItemBoletaInputSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('La boleta debe tener al menos un item')

        skus = [i['sku'] for i in items]
        productos = {p.sku: p for p in Producto.objects.filter(sku__in=skus, activo=True)}

        errores = []
        for item in items:
            sku = item['sku']
            if sku not in productos:
                errores.append(f'Producto "{sku}" no existe o está inactivo')
            elif productos[sku].stock < item['cantidad']:
                errores.append(
                    f'Stock insuficiente para "{sku}": '
                    f'disponible {productos[sku].stock}, solicitado {item["cantidad"]}'
                )
        if errores:
            raise serializers.ValidationError(errores)

        self._productos_cache = productos
        return items

    def validate_cliente(self, value):
        if value is None:
            return None
        from users.models import CustomUser
        try:
            return CustomUser.objects.get(pk=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError('Usuario no encontrado')

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        productos = getattr(self, '_productos_cache', {})

        es_staff = getattr(user, 'es_vendedor', False) or getattr(user, 'es_admin', False)
        vendedor = user if es_staff else None
        turno = None
        if vendedor:
            from turnos.models import TurnoCaja
            turno = TurnoCaja.objects.filter(
                vendedor=vendedor, estado=TurnoCaja.Estado.ABIERTO,
            ).first()

        cliente = validated_data.get('cliente')
        if not cliente and getattr(user, 'es_cliente', False):
            cliente = user

        igv_rate = Decimal(str(settings.IGV_PORCENTAJE))
        descuento_global = validated_data.get('descuento_global', Decimal('0.00'))

        detalles_data = []
        suma_detalles = Decimal('0.00')

        today = timezone.localdate()
        descuentos_mapa = {
            d.producto_id: d
            for d in Descuento.objects.filter(
                producto_id__in=list(productos.keys()),
                activo=True,
                fecha_inicio__lte=today,
                fecha_fin__gte=today,
            )
        }

        for item in validated_data['items']:
            producto = productos[item['sku']]
            precio_unitario = producto.precio
            cantidad = item['cantidad']

            descuento = descuentos_mapa.get(item['sku'])
            descuento_aplicado = Decimal('0.00')
            if descuento:
                if descuento.tipo == Descuento.Tipo.PORCENTAJE:
                    descuento_aplicado = (
                        precio_unitario * cantidad * descuento.valor / Decimal('100')
                    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                elif descuento.tipo == Descuento.Tipo.MONTO_FIJO:
                    desc_total = (descuento.valor * cantidad).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    descuento_aplicado = min(desc_total, precio_unitario * cantidad)
                elif descuento.tipo == Descuento.Tipo.NXM:
                    if descuento.lleva_n and descuento.paga_m:
                        sets_completos = cantidad // descuento.lleva_n
                        unidades_gratis = sets_completos * (descuento.lleva_n - descuento.paga_m)
                        descuento_aplicado = (precio_unitario * unidades_gratis).quantize(
                            Decimal('0.01'), rounding=ROUND_HALF_UP,
                        )

            subtotal_linea = (precio_unitario * cantidad - descuento_aplicado).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP,
            )
            suma_detalles += subtotal_linea
            detalles_data.append({
                'producto': producto,
                'cantidad': cantidad,
                'precio_unitario': precio_unitario,
                'descuento_aplicado': descuento_aplicado,
                'subtotal': subtotal_linea,
            })

        total = (suma_detalles - descuento_global).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if total < 0:
            raise serializers.ValidationError(
                {'descuento_global': 'El descuento global no puede superar el total de items'}
            )

        igv = (total * igv_rate / (1 + igv_rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        subtotal_sin_igv = total - igv

        now = timezone.now()
        if vendedor:
            Boleta.objects.filter(
                vendedor=vendedor,
                estado=Boleta.Estado.PENDIENTE,
                numero__isnull=True,
            ).update(
                estado=Boleta.Estado.ANULADA,
                anulada_fecha=now,
                anulada_por=vendedor,
                anulada_motivo='Reemplazada automáticamente al iniciar nueva cobranza',
            )
        elif cliente:
            Boleta.objects.filter(
                cliente=cliente,
                estado=Boleta.Estado.PENDIENTE,
                numero__isnull=True,
            ).update(
                estado=Boleta.Estado.ANULADA,
                anulada_fecha=now,
                anulada_por=cliente,
                anulada_motivo='Reemplazada automáticamente al iniciar nueva compra',
            )

        boleta = Boleta.objects.create(
            tipo=validated_data.get('tipo', Boleta.Tipo.BOLETA),
            cliente=cliente,
            vendedor=vendedor,
            turno=turno,
            subtotal=subtotal_sin_igv,
            igv=igv,
            descuento_global=descuento_global,
            total=total,
            estado=Boleta.Estado.PENDIENTE,
        )

        DetalleBoleta.objects.bulk_create([
            DetalleBoleta(boleta=boleta, **d) for d in detalles_data
        ])

        return boleta

class BoletaAnularSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=255, required=False, allow_blank=True)

class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoListSerializer(source='producto', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCarrito
        fields = ('id', 'producto', 'producto_detalle', 'cantidad', 'subtotal', 'agregado')
        read_only_fields = ('agregado',)

class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    cantidad_total = serializers.IntegerField(read_only=True)
    total_estimado = serializers.SerializerMethodField()

    class Meta:
        model = CarritoPersistente
        fields = ('cliente', 'items', 'cantidad_total', 'total_estimado', 'actualizado')

    def get_total_estimado(self, obj):
        total = sum(
            i.subtotal for i in obj.items.select_related('producto').all()
        )
        return str(Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class ItemCarritoWriteSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50)
    cantidad = serializers.IntegerField(min_value=1)

    def validate_sku(self, value):
        try:
            producto = Producto.objects.get(sku=value, activo=True)
        except Producto.DoesNotExist:
            raise serializers.ValidationError(f'Producto "{value}" no existe o está inactivo')
        self._producto = producto
        return value

class ItemCarritoCantidadSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=1)
