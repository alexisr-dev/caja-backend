from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from ventas.models import Boleta

class Pago(models.Model):
    class Metodo(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        MERCADOPAGO = 'MERCADOPAGO', 'Mercado Pago'

    class Submetodo(models.TextChoices):
        NINGUNO = 'NINGUNO', 'N/A'
        TARJETA = 'TARJETA', 'Tarjeta'
        YAPE = 'YAPE', 'Yape'
        PAGOEFECTIVO = 'PAGOEFECTIVO', 'PagoEfectivo'
        BILLETERA_MP = 'BILLETERA_MP', 'Billetera MP'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        APROBADO = 'APROBADO', 'Aprobado'
        RECHAZADO = 'RECHAZADO', 'Rechazado'
        REEMBOLSADO = 'REEMBOLSADO', 'Reembolsado'

    boleta = models.OneToOneField(
        Boleta, on_delete=models.CASCADE, related_name='pago',
    )
    metodo = models.CharField(max_length=15, choices=Metodo.choices)
    submetodo = models.CharField(
        max_length=15, choices=Submetodo.choices, default=Submetodo.NINGUNO,
    )

    monto = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Debe coincidir con boleta.total al momento del cobro.',
    )

    monto_recibido = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Solo EFECTIVO. Monto que entrego el cliente en cash.',
    )
    vuelto = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Solo EFECTIVO. Calculado: monto_recibido - monto.',
    )

    referencia_mp = models.CharField(
        max_length=100, blank=True,
        db_index=True,
        help_text='ID de transaccion devuelto por Mercado Pago.',
    )
    respuesta_gateway = models.JSONField(
        default=dict, blank=True,
        help_text='Respuesta cruda del gateway, para auditoria/debug.',
    )

    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.PENDIENTE,
    )

    fecha = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha']
        constraints = [
            models.UniqueConstraint(
                fields=['referencia_mp'],
                condition=~Q(referencia_mp=''),
                name='pago_referencia_mp_unica_cuando_existe',
            ),
            models.CheckConstraint(
                check=(
                    (Q(metodo='EFECTIVO') & Q(submetodo='NINGUNO'))
                    | (Q(metodo='MERCADOPAGO') & ~Q(submetodo='NINGUNO'))
                ),
                name='pago_submetodo_consistente',
            ),
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name='pago_monto_positivo',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.boleta.numero} - {self.get_metodo_display()} ({self.get_estado_display()})'

    def save(self, *args, **kwargs):
        if self.metodo == self.Metodo.EFECTIVO and self.monto_recibido is not None:
            self.vuelto = max(Decimal('0.00'), self.monto_recibido - self.monto)
        super().save(*args, **kwargs)

    @property
    def es_efectivo(self) -> bool:
        return self.metodo == self.Metodo.EFECTIVO

    @property
    def es_mp(self) -> bool:
        return self.metodo == self.Metodo.MERCADOPAGO
