from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):

    perfil_completo = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'first_name', 'last_name', 'rol',
            'telefono', 'direccion', 'dni',
            'avatar_url', 'perfil_completo',
        )
        read_only_fields = ('id', 'email', 'rol', 'avatar_url', 'perfil_completo')

class RegistroSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=9, required=False, allow_blank=True)
    dni = serializers.CharField(max_length=15, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        value = value.lower().strip()
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email ya registrado')
        return value

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data: dict) -> CustomUser:
        return CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data.get('last_name', ''),
            telefono=validated_data.get('telefono', ''),
            dni=validated_data.get('dni', ''),
            rol=CustomUser.Rol.CLIENTE,
        )

class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

class Login2FASerializer(serializers.Serializer):

    session_token = serializers.CharField()
    codigo = serializers.RegexField(regex=r'^\d{6}$', max_length=6)

class PerfilUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'telefono', 'direccion', 'dni')

class PasswordResetRequestSerializer(serializers.Serializer):

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

class PasswordResetConfirmSerializer(serializers.Serializer):

    codigo = serializers.RegexField(regex=r'^\d{6}$', max_length=6)
    nueva_password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    def validate_nueva_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

class UsuarioAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'first_name', 'last_name', 'rol',
            'telefono', 'dni', 'is_active', 'fecha_registro',
        )
        read_only_fields = ('id', 'fecha_registro')

    def validate_email(self, value):
        value = value.lower().strip()
        qs = CustomUser.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este email ya está en uso.')
        return value

class CrearUsuarioAdminSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    rol = serializers.ChoiceField(choices=['ADMIN', 'VENDEDOR', 'CLIENTE'])
    telefono = serializers.CharField(max_length=9, required=False, allow_blank=True, default='')
    dni = serializers.CharField(max_length=15, required=False, allow_blank=True, default='')

    def validate_email(self, value):
        value = value.lower().strip()
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email ya registrado.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        return CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data.get('last_name', ''),
            rol=validated_data['rol'],
            telefono=validated_data.get('telefono', ''),
            dni=validated_data.get('dni', ''),
        )

class GoogleSignInSerializer(serializers.Serializer):

    id_token = serializers.CharField()
    fcm_token = serializers.CharField(required=False, allow_blank=True)
    plataforma = serializers.ChoiceField(
        choices=['ANDROID', 'IOS'],
        required=False,
        default='ANDROID',
    )
