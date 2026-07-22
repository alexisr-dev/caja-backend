from django.conf import settings
from django.db import models
from django.db.models import Q

class DispositivoFCM(models.Model):

    class Plataforma(models.TextChoices):
        ANDROID = 'ANDROID', 'Android'
        IOS = 'IOS', 'iOS'
        WEB = 'WEB', 'Web'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='dispositivos_fcm',
    )
    token_fcm = models.CharField(max_length=500, unique=True)
    plataforma = models.CharField(max_length=10, choices=Plataforma.choices)
    activo = models.BooleanField(default=True)
    registrado = models.DateTimeField(auto_now_add=True)
    ultima_actividad = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dispositivo FCM'
        verbose_name_plural = 'Dispositivos FCM'
        indexes = [
            models.Index(
                fields=['usuario'],
                condition=Q(activo=True),
                name='fcm_usuario_activo_idx',
            ),
        ]

    def __str__(self) -> str:
        marca = '[on]' if self.activo else '[off]'
        return f'{marca} {self.get_plataforma_display()} - {self.usuario.email}'

class Notificacion(models.Model):

    class Tipo(models.TextChoices):
        COMPRA_EXITOSA = 'COMPRA_EXITOSA', 'Compra exitosa'
        OFERTA = 'OFERTA', 'Oferta'
        STOCK_DISPONIBLE = 'STOCK_DISPONIBLE', 'Producto favorito disponible'
        SISTEMA = 'SISTEMA', 'Sistema'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()
    data = models.JSONField(
        default=dict, blank=True,
        help_text='Payload extra (ej: boleta_id para deep linking).',
    )
    leida = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificacion'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_envio']
        indexes = [
            models.Index(
                fields=['usuario', '-fecha_envio'],
                condition=Q(leida=False),
                name='notif_usuario_no_leidas_idx',
            ),
        ]

    def __str__(self) -> str:
        marca = '[!]' if not self.leida else '[x]'
        return f'{marca} {self.usuario.email}: {self.titulo}'

    def marcar_leida(self):
        if not self.leida:
            self.leida = True
            self.save(update_fields=['leida'])
