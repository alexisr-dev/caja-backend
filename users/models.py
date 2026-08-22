import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .managers import CustomUserManager


def _hash_codigo(codigo: str) -> str:
    """Devuelve HMAC-SHA256 del código OTP. Se almacena en BD en lugar del texto claro."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        codigo.encode(),
        hashlib.sha256,
    ).hexdigest()

class CustomUser(AbstractUser):

    class Rol(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente'
        VENDEDOR = 'VENDEDOR', 'Vendedor'
        ADMIN = 'ADMIN', 'Administrador'

    email = models.EmailField('Email', unique=True)

    rol = models.CharField(
        'Rol',
        max_length=20,
        choices=Rol.choices,
        default=Rol.CLIENTE,
        db_index=True,
    )

    telefono = models.CharField(
        'Celular',
        max_length=9,
        blank=True,
        validators=[RegexValidator(
            r'^9\d{8}$',
            'Numero de celular peruano: 9 digitos, empieza con 9 (ej: 969929157)',
        )],
        help_text='Celular peruano de 9 digitos. Requerido para pagos con Yape.',
    )
    direccion = models.CharField('Direccion', max_length=255, blank=True)

    dni = models.CharField(
        'DNI / CE',
        max_length=15,
        blank=True,
        help_text='DNI peruano (8 digitos) o Carne de Extranjeria',
    )

    fecha_registro = models.DateTimeField('Fecha de registro', auto_now_add=True)

    google_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True,
        help_text='Google "sub" claim. Solo se llena si el usuario inicia con Google.',
    )
    avatar_url = models.URLField(blank=True)

    es_demo = models.BooleanField(
        'Cuenta demo',
        default=False,
        db_index=True,
        help_text='Cuenta de demostracion: omite la verificacion 2FA de 6 digitos al iniciar sesion.',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    @property
    def perfil_completo(self) -> bool:
        return bool(self.dni)

    @property
    def es_cliente(self) -> bool:
        return self.rol == self.Rol.CLIENTE

    @property
    def es_vendedor(self) -> bool:
        return self.rol == self.Rol.VENDEDOR

    @property
    def es_admin(self) -> bool:
        return self.rol == self.Rol.ADMIN

    def __str__(self) -> str:
        return f'{self.email} ({self.get_rol_display()})'

class TokenRecuperacionPassword(models.Model):

    DURACION_MINUTOS = 30

    usuario = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='tokens_reset',
    )
    codigo = models.CharField(max_length=64)
    expira = models.DateTimeField()
    usado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Token de recuperacion'
        verbose_name_plural = 'Tokens de recuperacion'
        ordering = ['-creado']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'codigo'],
                condition=models.Q(usado=False),
                name='unique_token_reset_activo_por_usuario',
            )
        ]

    @classmethod
    def generar(cls, usuario: 'CustomUser') -> tuple['TokenRecuperacionPassword', str]:
        cls.objects.filter(usuario=usuario, usado=False).update(usado=True)
        codigo_claro = f'{secrets.randbelow(1_000_000):06d}'
        obj = cls.objects.create(
            usuario=usuario,
            codigo=_hash_codigo(codigo_claro),
            expira=timezone.now() + timedelta(minutes=cls.DURACION_MINUTOS),
        )
        return obj, codigo_claro

    def es_valido(self) -> bool:
        return not self.usado and timezone.now() < self.expira

    def __str__(self) -> str:
        estado = 'usado' if self.usado else ('valido' if self.es_valido() else 'expirado')
        return f'{self.usuario.email} [{estado}]'

class CodigoVerificacion2FA(models.Model):

    DURACION_MINUTOS = 10

    usuario = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='codigos_2fa',
    )
    codigo = models.CharField(max_length=64)
    expira = models.DateTimeField()
    usado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Codigo 2FA'
        verbose_name_plural = 'Codigos 2FA'
        ordering = ['-creado']

    @classmethod
    def generar(cls, usuario: 'CustomUser') -> tuple['CodigoVerificacion2FA', str]:
        cls.objects.filter(usuario=usuario, usado=False).update(usado=True)
        codigo_claro = f'{secrets.randbelow(1_000_000):06d}'
        obj = cls.objects.create(
            usuario=usuario,
            codigo=_hash_codigo(codigo_claro),
            expira=timezone.now() + timedelta(minutes=cls.DURACION_MINUTOS),
        )
        return obj, codigo_claro

    def es_valido(self) -> bool:
        return not self.usado and timezone.now() < self.expira

    def __str__(self) -> str:
        return f'2FA {self.usuario.email} ({self.codigo})'
