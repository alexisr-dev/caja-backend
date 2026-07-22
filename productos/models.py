from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import F, Q

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    imagen_icono = models.ImageField(upload_to='categorias/', blank=True, null=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre

class Proveedor(models.Model):

    ruc = models.CharField(
        'RUC',
        max_length=11,
        unique=True,
        validators=[RegexValidator(
            r'^(10|15|17|20)\d{9}$',
            'RUC peruano: 11 digitos, empieza con 10, 15, 17 o 20',
        )],
    )
    razon_social = models.CharField(max_length=200)
    telefono = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(
            r'^\+?\d{6,15}$',
            'Telefono entre 6 y 15 digitos',
        )],
        help_text='Puede ser fijo, celular o internacional',
    )
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    persona_contacto = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['razon_social']

    def __str__(self) -> str:
        return f'{self.ruc} - {self.razon_social}'

class Producto(models.Model):

    sku = models.CharField(
        primary_key=True,
        max_length=50,
        validators=[RegexValidator(
            r'^[A-Za-z0-9_\-]+$',
            'SKU solo permite letras (A-Z), numeros, guion y guion bajo. '
            'Sin Ñ, acentos ni espacios.',
        )],
        help_text=(
            'Convencion: <CATEGORIA>-<correlativo> (ej: BEB-001, CON-001). '
            'Debe coincidir EXACTAMENTE con el prefijo del id_chroma en ChromaDB '
            '(el ia-service hace split("_")[0] para extraerlo).'
        ),
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Precio INCLUYE IGV 18%',
    )

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name='productos',
    )
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT,
        related_name='productos', null=True, blank=True,
    )
    padre = models.ForeignKey(
        'self', on_delete=models.CASCADE, related_name='variantes',
        null=True, blank=True,
        help_text='Si es variante, apunta al producto padre',
    )

    stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    stock_minimo = models.IntegerField(
        default=5,
        validators=[MinValueValidator(0)],
        help_text='Cuando stock <= stock_minimo se genera alerta',
    )
    fecha_vencimiento = models.DateField(null=True, blank=True)

    imagen_principal = models.ImageField(upload_to='productos/', blank=True, null=True)

    contador_ventas = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total unidades vendidas. Se actualiza por signal al pagar boleta.',
    )

    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['activo', 'padre'], name='prod_activo_padre_idx'),
            models.Index(fields=['fecha_vencimiento'], name='prod_vencimiento_idx',
                         condition=Q(fecha_vencimiento__isnull=False)),
            models.Index(fields=['-contador_ventas'], name='prod_top_ventas_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(precio__gt=0),
                name='producto_precio_positivo',
            ),
            models.CheckConstraint(
                check=Q(stock__gte=0),
                name='producto_stock_no_negativo',
            ),
        ]

    def __str__(self) -> str:
        if self.padre:
            return f'{self.padre.nombre} - {self.nombre}'
        return self.nombre

    @property
    def es_padre(self) -> bool:
        return self.variantes.exists()

    @property
    def es_variante(self) -> bool:
        return self.padre_id is not None

    @property
    def stock_bajo(self) -> bool:
        return self.stock <= self.stock_minimo

class FotoProducto(models.Model):

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='fotos',
    )
    imagen = models.ImageField(upload_to='productos_fotos/')
    orden = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto de producto'
        verbose_name_plural = 'Fotos de productos'
        ordering = ['orden', 'creado']

    def __str__(self) -> str:
        return f'Foto {self.orden} de {self.producto.sku}'

class HistorialPrecio(models.Model):

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='historial_precios',
    )
    precio_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    precio_nuevo = models.DecimalField(max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Historial de precio'
        verbose_name_plural = 'Historial de precios'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['producto', '-fecha'], name='historial_prod_fecha_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.producto.sku}: {self.precio_anterior} -> {self.precio_nuevo}'

class Descuento(models.Model):

    class Tipo(models.TextChoices):
        PORCENTAJE = 'PORCENTAJE', '% descuento'
        MONTO_FIJO = 'MONTO_FIJO', 'Monto fijo S/'
        NXM = 'NXM', 'N por M (2x1, 3x2)'

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='descuentos',
    )
    tipo = models.CharField(max_length=15, choices=Tipo.choices)

    valor = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text='Para PORCENTAJE (0-100) o MONTO_FIJO (>0). Vacio si tipo=NXM.',
    )
    lleva_n = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(2)],
        help_text='Solo NXM: cantidad que lleva el cliente',
    )
    paga_m = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        help_text='Solo NXM: cantidad que paga (debe ser < lleva_n)',
    )

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Descuento'
        verbose_name_plural = 'Descuentos'
        constraints = [
            models.CheckConstraint(
                check=Q(fecha_fin__gte=F('fecha_inicio')),
                name='descuento_fechas_validas',
            ),
        ]

    def __str__(self) -> str:
        if self.tipo == self.Tipo.PORCENTAJE:
            return f'{self.producto.sku}: -{self.valor}%'
        if self.tipo == self.Tipo.MONTO_FIJO:
            return f'{self.producto.sku}: -S/ {self.valor}'
        return f'{self.producto.sku}: {self.lleva_n}x{self.paga_m}'

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            errors['fecha_fin'] = 'fecha_fin debe ser >= fecha_inicio'

        if self.tipo == self.Tipo.PORCENTAJE:
            if self.valor is None or not (0 < self.valor <= 100):
                errors['valor'] = 'Porcentaje debe estar entre 0 y 100'
        elif self.tipo == self.Tipo.MONTO_FIJO:
            if self.valor is None or self.valor <= 0:
                errors['valor'] = 'Monto fijo debe ser > 0'
        elif self.tipo == self.Tipo.NXM:
            if not self.lleva_n or not self.paga_m:
                errors['lleva_n'] = 'NXM requiere lleva_n y paga_m'
            elif self.paga_m >= self.lleva_n:
                errors['paga_m'] = 'paga_m debe ser menor que lleva_n'

        if errors:
            raise ValidationError(errors)

class Favorito(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favoritos',
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='fav_por',
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        ordering = ['-creado']
        constraints = [
            models.UniqueConstraint(
                fields=['cliente', 'producto'],
                name='favorito_cliente_producto_unique',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.cliente.email} -> {self.producto.sku}'

class MovimientoStock(models.Model):

    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida (venta)'
        AJUSTE = 'AJUSTE', 'Ajuste manual'
        ANULACION = 'ANULACION', 'Devolucion por anulacion'

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='movimientos',
    )
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    cantidad = models.IntegerField(
        help_text='Magnitud del movimiento. Solo AJUSTE puede ser negativo.',
    )
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    motivo = models.CharField(max_length=255, blank=True)
    boleta = models.ForeignKey(
        'ventas.Boleta', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_stock',
    )

    class Meta:
        verbose_name = 'Movimiento de stock'
        verbose_name_plural = 'Movimientos de stock'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['producto', '-fecha'], name='movstock_prod_fecha_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.producto.sku} {self.get_tipo_display()} x{self.cantidad}'
