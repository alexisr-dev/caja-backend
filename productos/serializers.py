from decimal import Decimal

from rest_framework import serializers

from .models import (
    Categoria,
    Proveedor,
    Producto,
    FotoProducto,
    HistorialPrecio,
    Descuento,
    Favorito,
    MovimientoStock,
)

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ('id', 'nombre', 'descripcion', 'imagen_icono')

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = (
            'id', 'ruc', 'razon_social', 'telefono',
            'email', 'direccion', 'persona_contacto', 'activo',
        )

class FotoProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoProducto
        fields = ('id', 'imagen', 'orden', 'creado')
        read_only_fields = ('creado',)

class DescuentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Descuento
        fields = (
            'id', 'producto', 'tipo', 'valor',
            'lleva_n', 'paga_m', 'fecha_inicio', 'fecha_fin', 'activo',
        )

    def validate(self, attrs):
        tipo = attrs.get('tipo', getattr(self.instance, 'tipo', None))
        valor = attrs.get('valor', getattr(self.instance, 'valor', None))
        lleva_n = attrs.get('lleva_n', getattr(self.instance, 'lleva_n', None))
        paga_m = attrs.get('paga_m', getattr(self.instance, 'paga_m', None))
        fecha_inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fecha_fin = attrs.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({'fecha_fin': 'fecha_fin debe ser >= fecha_inicio'})

        if tipo == Descuento.Tipo.PORCENTAJE:
            if valor is None or not (Decimal('0') < valor <= Decimal('100')):
                raise serializers.ValidationError({'valor': 'Porcentaje debe estar entre 0 y 100'})
        elif tipo == Descuento.Tipo.MONTO_FIJO:
            if valor is None or valor <= 0:
                raise serializers.ValidationError({'valor': 'Monto fijo debe ser > 0'})
        elif tipo == Descuento.Tipo.NXM:
            if not lleva_n or not paga_m:
                raise serializers.ValidationError({'lleva_n': 'NXM requiere lleva_n y paga_m'})
            if paga_m >= lleva_n:
                raise serializers.ValidationError({'paga_m': 'paga_m debe ser menor que lleva_n'})
        return attrs

class ProductoListSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    stock_bajo = serializers.BooleanField(read_only=True)
    primera_foto = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = (
            'sku', 'nombre', 'precio', 'stock', 'stock_bajo',
            'imagen_principal', 'primera_foto', 'categoria_nombre', 'activo',
            'contador_ventas', 'fecha_vencimiento',
        )

    def get_primera_foto(self, obj):
        foto = obj.fotos.order_by('orden', 'creado').first()
        if foto and foto.imagen:
            request = self.context.get('request')
            url = foto.imagen.url
            return request.build_absolute_uri(url) if request else url
        return None

class ProductoDetailSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    proveedor = ProveedorSerializer(read_only=True)
    fotos = FotoProductoSerializer(many=True, read_only=True)
    descuentos_activos = serializers.SerializerMethodField()
    variantes = ProductoListSerializer(many=True, read_only=True)
    es_padre = serializers.BooleanField(read_only=True)
    es_variante = serializers.BooleanField(read_only=True)
    stock_bajo = serializers.BooleanField(read_only=True)
    class Meta:
        model = Producto
        fields = (
            'sku', 'nombre', 'descripcion', 'precio',
            'stock', 'stock_minimo', 'stock_bajo',
            'fecha_vencimiento', 'imagen_principal',
            'categoria', 'proveedor', 'padre',
            'es_padre', 'es_variante', 'variantes',
            'fotos', 'descuentos_activos',
            'contador_ventas', 'activo', 'creado', 'actualizado',
        )

    def get_descuentos_activos(self, obj):
        from django.utils import timezone
        hoy = timezone.now().date()
        qs = obj.descuentos.filter(activo=True, fecha_inicio__lte=hoy, fecha_fin__gte=hoy)
        return DescuentoSerializer(qs, many=True).data

class ProductoWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Producto
        fields = (
            'sku', 'nombre', 'descripcion', 'precio',
            'stock', 'stock_minimo', 'fecha_vencimiento',
            'imagen_principal', 'categoria', 'proveedor', 'padre',
            'activo',
        )

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError('El precio debe ser mayor a 0')
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError('El stock no puede ser negativo')
        return value

class HistorialPrecioSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True, default=None)

    class Meta:
        model = HistorialPrecio
        fields = ('id', 'precio_anterior', 'precio_nuevo', 'usuario_email', 'fecha', 'motivo')

class AjusteStockSerializer(serializers.Serializer):

    TIPOS_MANUALES = [MovimientoStock.Tipo.ENTRADA, MovimientoStock.Tipo.AJUSTE]

    tipo = serializers.ChoiceField(choices=TIPOS_MANUALES)
    cantidad = serializers.IntegerField()
    motivo = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        tipo = attrs['tipo']
        cantidad = attrs['cantidad']
        if tipo == MovimientoStock.Tipo.ENTRADA and cantidad <= 0:
            raise serializers.ValidationError({'cantidad': 'ENTRADA requiere cantidad > 0'})
        return attrs

class MovimientoStockSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True, default=None)

    class Meta:
        model = MovimientoStock
        fields = ('id', 'tipo', 'cantidad', 'fecha', 'usuario_email', 'motivo', 'boleta')

class FavoritoSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoListSerializer(source='producto', read_only=True)
    sku = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Favorito
        fields = ('id', 'producto', 'producto_detalle', 'creado', 'sku')
        read_only_fields = ('creado',)
        extra_kwargs = {'producto': {'required': False}}

    def validate(self, data):
        sku = data.pop('sku', None)
        if sku and 'producto' not in data:
            try:
                data['producto'] = Producto.objects.get(sku=sku)
            except Producto.DoesNotExist:
                raise serializers.ValidationError({'sku': 'Producto no encontrado'})
        if 'producto' not in data:
            raise serializers.ValidationError({'producto': 'Se requiere producto o sku'})
        request = self.context['request']
        if Favorito.objects.filter(cliente=request.user, producto=data['producto']).exists():
            raise serializers.ValidationError({'detail': 'Ya tienes este producto en favoritos'})
        return data

    def create(self, validated_data):
        validated_data['cliente'] = self.context['request'].user
        return super().create(validated_data)

