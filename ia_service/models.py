from django.conf import settings
from django.db import models

from productos.models import Producto

class LogEscaneoIA(models.Model):
    class Resultado(models.TextChoices):
        OK = 'OK', 'Reconocido'
        NO_DETECTADO = 'NO_DETECTADO', 'No detecto'
        DESCONOCIDO = 'DESCONOCIDO', 'Producto desconocido'
        SKU_NO_EXISTE = 'SKU_NO_EXISTE', 'SKU devuelto no existe en BD'
        ERROR = 'ERROR', 'Error de servicio'

    class Modo(models.TextChoices):
        MOVIL = 'MOVIL', 'Movil (cliente)'
        CAJA = 'CAJA', 'Caja (vendedor)'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='escaneos',
    )
    modo = models.CharField(max_length=10, choices=Modo.choices)
    producto_detectado = models.ForeignKey(
        Producto, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    resultado = models.CharField(max_length=15, choices=Resultado.choices)

    confianza = models.FloatField(null=True, blank=True)
    latencia_ms = models.IntegerField(null=True, blank=True)

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de escaneo IA'
        verbose_name_plural = 'Logs de escaneo IA'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha'], name='log_ia_fecha_idx'),
        ]

    def __str__(self) -> str:
        det = self.producto_detectado.sku if self.producto_detectado else '-'
        return f'{self.fecha:%Y-%m-%d %H:%M} {self.resultado} {det}'
