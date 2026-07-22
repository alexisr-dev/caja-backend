from rest_framework import serializers

from .models import Alerta

class AlertaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    nivel_display = serializers.CharField(source='get_nivel_display', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True, default=None)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True, default=None)

    class Meta:
        model = Alerta
        fields = (
            'id', 'tipo', 'tipo_display', 'nivel', 'nivel_display',
            'mensaje', 'producto_sku', 'producto_nombre', 'leida', 'fecha',
        )
        read_only_fields = fields
