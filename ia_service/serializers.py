from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes

from .models import LogEscaneoIA

@extend_schema_field(OpenApiTypes.BINARY)
class ImageUploadField(serializers.ImageField):
    pass

class EscanearSerializer(serializers.Serializer):
    imagen = ImageUploadField()

class RegistroVisualSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50)
    sufijo = serializers.CharField(
        max_length=30, default='principal',
        help_text='Sufijo del id_chroma: frontal, lateral, detalle, etc.',
    )
    imagen = ImageUploadField()

    def validate_sku(self, value):
        from productos.models import Producto
        if not Producto.objects.filter(sku=value).exists():
            raise serializers.ValidationError(f'Producto con SKU "{value}" no existe')
        return value

class LogEscaneoSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True, default=None)
    producto_sku = serializers.CharField(
        source='producto_detectado.sku', read_only=True, default=None,
    )

    class Meta:
        model = LogEscaneoIA
        fields = (
            'id', 'modo', 'resultado', 'confianza', 'latencia_ms',
            'usuario_email', 'producto_sku', 'fecha',
        )
