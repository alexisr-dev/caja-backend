from decimal import Decimal

from rest_framework import serializers

from .models import TurnoCaja

class TurnoSerializer(serializers.ModelSerializer):
    vendedor_email = serializers.EmailField(source='vendedor.email', read_only=True)
    total_ventas_efectivo = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )
    esperado_en_caja = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )
    diferencia = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True, allow_null=True,
    )
    diagnostico = serializers.CharField(read_only=True)

    class Meta:
        model = TurnoCaja
        fields = (
            'id', 'vendedor', 'vendedor_email', 'estado',
            'apertura_fecha', 'monto_inicial',
            'cierre_fecha', 'monto_contado_cierre',
            'total_ventas_efectivo', 'esperado_en_caja',
            'diferencia', 'diagnostico', 'observaciones',
        )
        read_only_fields = ('id', 'vendedor', 'apertura_fecha', 'estado')

class TurnoAbrirSerializer(serializers.Serializer):
    monto_inicial = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        min_value=Decimal('0.00'),
    )

class TurnoCerrarSerializer(serializers.Serializer):
    monto_contado_cierre = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        min_value=Decimal('0.00'),
    )
    observaciones = serializers.CharField(
        max_length=1000, required=False, allow_blank=True,
    )
