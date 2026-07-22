from django.db import models
from django.db.models import Q

from productos.models import Producto

class Alerta(models.Model):
    class Tipo(models.TextChoices):
        STOCK_BAJO = 'STOCK_BAJO', 'Stock bajo'
        STOCK_AGOTADO = 'STOCK_AGOTADO', 'Stock agotado'
        VENCIMIENTO_CERCANO = 'VENCIMIENTO_CERCANO', 'Proximo a vencer'
        SISTEMA = 'SISTEMA', 'Sistema'
        PAGO_FALLIDO = 'PAGO_FALLIDO', 'Pago fallido'

    class Nivel(models.TextChoices):
        INFO = 'INFO', 'Info'
        ADVERTENCIA = 'ADVERTENCIA', 'Advertencia'
        CRITICO = 'CRITICO', 'Critico'

    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    nivel = models.CharField(max_length=15, choices=Nivel.choices, default=Nivel.INFO)
    mensaje = models.CharField(max_length=500)

    producto = models.ForeignKey(
        Producto, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='alertas',
    )

    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-fecha']
        indexes = [
            models.Index(
                fields=['-fecha'],
                condition=Q(leida=False),
                name='alerta_no_leidas_idx',
            ),
        ]

    def __str__(self) -> str:
        marca = '[!]' if not self.leida else '[x]'
        return f'{marca} {self.get_tipo_display()} - {self.mensaje[:60]}'

    def marcar_leida(self):
        if not self.leida:
            self.leida = True
            self.save(update_fields=['leida'])
