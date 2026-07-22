from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from productos.models import Producto

class Boleta(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADA = 'PAGADA', 'Pagada'
        ANULADA = 'ANULADA', 'Anulada'

    class Tipo(models.TextChoices):
        BOLETA = 'BOLETA', 'Boleta'
        TICKET = 'TICKET', 'Ticket'

    numero = models.CharField(max_length=30, unique=True, editable=False, null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.BOLETA)

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='boletas_cliente',
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='boletas_vendedor',
    )
    turno = models.ForeignKey(
        'turnos.TurnoCaja', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='boletas',
    )

    fecha = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    igv = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    descuento_global = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.PENDIENTE,
    )

    anulada_fecha = models.DateTimeField(null=True, blank=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='boletas_anuladas',
    )
    anulada_motivo = models.CharField(max_length=255, blank=True)

    pdf_url = models.FileField(upload_to='boletas/', blank=True, null=True)

    class Meta:
        verbose_name = 'Boleta'
        verbose_name_plural = 'Boletas'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['estado', 'fecha'], name='boleta_estado_fecha_idx'),
            models.Index(fields=['cliente', '-fecha'], name='boleta_cliente_fecha_idx'),
            models.Index(fields=['turno', 'estado'], name='boleta_turno_estado_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(total__gte=0),
                name='boleta_total_no_negativo',
            ),
            models.CheckConstraint(
                check=(
                    ~Q(estado='ANULADA')
                    | (
                        Q(estado='ANULADA')
                        & Q(anulada_fecha__isnull=False)
                        & Q(anulada_por__isnull=False)
                    )
                ),
                name='boleta_anulacion_consistente',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.numero or f"borrador-{self.pk}"} ({self.get_estado_display()})'

    def asignar_numero(self) -> None:
        if self.numero:
            return
        with transaction.atomic():
            ano = timezone.now().year
            prefijo = f'B-{ano}-'
            ultimo = (
                Boleta.objects
                .select_for_update()
                .filter(numero__startswith=prefijo)
                .order_by('-numero')
                .first()
            )
            correlativo = int(ultimo.numero.split('-')[-1]) + 1 if ultimo else 1
            self.numero = f'{prefijo}{correlativo:05d}'
            self.save(update_fields=['numero'])

class DetalleBoleta(models.Model):

    boleta = models.ForeignKey(
        Boleta, on_delete=models.CASCADE, related_name='detalles',
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name='+',
    )
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Precio del producto al momento de la venta (snapshot, no cambia).',
    )
    descuento_aplicado = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Calculado: cantidad * precio_unitario - descuento_aplicado',
    )

    class Meta:
        verbose_name = 'Detalle de boleta'
        verbose_name_plural = 'Detalles de boleta'
        constraints = [
            models.CheckConstraint(
                check=Q(cantidad__gte=1),
                name='detalle_cantidad_minima',
            ),
            models.CheckConstraint(
                check=Q(subtotal__gte=0),
                name='detalle_subtotal_no_negativo',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.boleta.numero or f"boleta-{self.boleta_id}"}: {self.producto.sku} x{self.cantidad}'

class CarritoPersistente(models.Model):
    cliente = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carrito',
        primary_key=True,
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Carrito persistente'
        verbose_name_plural = 'Carritos persistentes'

    def __str__(self) -> str:
        return f'Carrito de {self.cliente.email}'

    @property
    def cantidad_total(self) -> int:
        return sum(i.cantidad for i in self.items.all())

class ItemCarrito(models.Model):

    carrito = models.ForeignKey(
        CarritoPersistente, on_delete=models.CASCADE, related_name='items',
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='+',
    )
    cantidad = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item de carrito'
        verbose_name_plural = 'Items de carrito'
        ordering = ['-agregado']
        constraints = [
            models.UniqueConstraint(
                fields=['carrito', 'producto'],
                name='item_carrito_producto_unico',
            ),
            models.CheckConstraint(
                check=Q(cantidad__gte=1),
                name='item_cantidad_minima',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.producto.sku} x{self.cantidad} ({self.carrito.cliente.email})'

    @property
    def subtotal(self) -> Decimal:
        return self.producto.precio * self.cantidad
