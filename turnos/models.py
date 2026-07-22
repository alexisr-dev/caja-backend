from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum

class TurnoCaja(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = 'ABIERTO', 'Abierto'
        CERRADO = 'CERRADO', 'Cerrado'

    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='turnos',
    )

    apertura_fecha = models.DateTimeField(auto_now_add=True)
    monto_inicial = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Efectivo con el que abre la caja (cambio inicial).',
    )

    cierre_fecha = models.DateTimeField(null=True, blank=True)
    monto_contado_cierre = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Efectivo contado fisicamente al cerrar.',
    )

    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.ABIERTO,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Turno de caja'
        verbose_name_plural = 'Turnos de caja'
        ordering = ['-apertura_fecha']
        constraints = [
            models.UniqueConstraint(
                fields=['vendedor'],
                condition=Q(estado='ABIERTO'),
                name='turno_unico_abierto_por_vendedor',
            ),
            models.CheckConstraint(
                check=(
                    Q(estado='ABIERTO', cierre_fecha__isnull=True,
                      monto_contado_cierre__isnull=True)
                    | Q(estado='CERRADO', cierre_fecha__isnull=False,
                        monto_contado_cierre__isnull=False)
                ),
                name='turno_cierre_consistente',
            ),
        ]

    def __str__(self) -> str:
        return f'Turno #{self.pk} {self.vendedor.email} [{self.get_estado_display()}]'

    @property
    def total_ventas_efectivo(self) -> Decimal:
        from ventas.models import Boleta
        total = Boleta.objects.filter(
            turno=self,
            estado='PAGADA',
            pago__metodo='EFECTIVO',
        ).aggregate(s=Sum('total'))['s']
        return total or Decimal('0.00')

    @property
    def esperado_en_caja(self) -> Decimal:
        return self.monto_inicial + self.total_ventas_efectivo

    @property
    def diferencia(self) -> Decimal | None:
        if self.monto_contado_cierre is None:
            return None
        return self.monto_contado_cierre - self.esperado_en_caja

    @property
    def diagnostico(self) -> str:
        diff = self.diferencia
        if diff is None:
            return 'TURNO ABIERTO'
        if diff == 0:
            return 'CUADRE EXACTO'
        if diff > 0:
            return f'SOBRA S/ {diff}'
        return f'FALTA S/ {abs(diff)}'

    @property
    def esta_abierto(self) -> bool:
        return self.estado == self.Estado.ABIERTO
