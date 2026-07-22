from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from ventas.models import Boleta
from .models import Pago

class PagoSerializer(serializers.ModelSerializer):
    metodo_display = serializers.CharField(source='get_metodo_display', read_only=True)
    submetodo_display = serializers.CharField(source='get_submetodo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    boleta_numero = serializers.CharField(source='boleta.numero', read_only=True)

    class Meta:
        model = Pago
        fields = (
            'id', 'boleta', 'boleta_numero', 'metodo', 'metodo_display',
            'submetodo', 'submetodo_display',
            'monto', 'monto_recibido', 'vuelto',
            'referencia_mp', 'estado', 'estado_display',
            'fecha', 'actualizado',
        )
        read_only_fields = fields

class PagoEfectivoSerializer(serializers.Serializer):
    boleta_id = serializers.IntegerField()
    monto_recibido = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))

    def validate_boleta_id(self, value):
        try:
            boleta = Boleta.objects.get(pk=value)
        except Boleta.DoesNotExist:
            raise serializers.ValidationError('Boleta no encontrada')
        if boleta.estado != Boleta.Estado.PENDIENTE:
            raise serializers.ValidationError(
                f'La boleta ya fue procesada (estado: {boleta.estado})'
            )
        if hasattr(boleta, 'pago') and boleta.pago.estado != Pago.Estado.RECHAZADO:
            raise serializers.ValidationError('Esta boleta ya tiene un pago registrado')
        self._boleta = boleta
        return value

    def validate(self, attrs):
        boleta = getattr(self, '_boleta', None)
        if boleta and attrs['monto_recibido'] < boleta.total:
            raise serializers.ValidationError({
                'monto_recibido': (
                    f'Monto insuficiente. Total boleta: S/ {boleta.total}, '
                    f'recibido: S/ {attrs["monto_recibido"]}'
                )
            })
        return attrs

class PagoMPTarjetaSerializer(serializers.Serializer):
    boleta_id = serializers.IntegerField()
    token_mp = serializers.CharField(
        help_text='Card token generado por el SDK JS de Mercado Pago en el frontend (PCI).'
    )
    cuotas = serializers.IntegerField(default=1, min_value=1, max_value=24)
    email_pagador = serializers.EmailField()
    tipo_doc = serializers.ChoiceField(choices=['DNI', 'CE', 'RUC'], default='DNI')
    num_doc = serializers.CharField(max_length=15)
    payment_method_id = serializers.CharField(max_length=30, default='', allow_blank=True)
    issuer_id = serializers.CharField(max_length=20, default='', allow_blank=True)

    def validate(self, attrs):
        tipo = attrs.get('tipo_doc', 'DNI')
        num  = attrs.get('num_doc', '')
        if num and not num.isdigit():
            raise serializers.ValidationError({'num_doc': 'El documento solo acepta dígitos'})
        if not settings.DEBUG:
            if tipo == 'DNI' and len(num) != 8:
                raise serializers.ValidationError({'num_doc': 'DNI peruano debe tener exactamente 8 dígitos'})
            if tipo == 'RUC' and len(num) != 11:
                raise serializers.ValidationError({'num_doc': 'RUC debe tener exactamente 11 dígitos'})
        return attrs

    def validate_boleta_id(self, value):
        try:
            boleta = Boleta.objects.get(pk=value)
        except Boleta.DoesNotExist:
            raise serializers.ValidationError('Boleta no encontrada')
        if boleta.estado != Boleta.Estado.PENDIENTE:
            raise serializers.ValidationError(f'Boleta ya procesada (estado: {boleta.estado})')
        if hasattr(boleta, 'pago') and boleta.pago.estado != Pago.Estado.RECHAZADO:
            raise serializers.ValidationError('Esta boleta ya tiene un pago registrado')
        self._boleta = boleta
        return value

class PagoMPYapeSerializer(serializers.Serializer):
    YAPE_MONTO_MINIMO = Decimal('5.00')

    boleta_id = serializers.IntegerField()
    numero_celular = serializers.CharField(max_length=9, min_length=9)
    otp = serializers.CharField(max_length=6, min_length=6)
    email_pagador = serializers.EmailField()

    def validate_boleta_id(self, value):
        try:
            boleta = Boleta.objects.get(pk=value)
        except Boleta.DoesNotExist:
            raise serializers.ValidationError('Boleta no encontrada')
        if boleta.estado != Boleta.Estado.PENDIENTE:
            raise serializers.ValidationError(f'Boleta ya procesada (estado: {boleta.estado})')
        if hasattr(boleta, 'pago') and boleta.pago.estado != Pago.Estado.RECHAZADO:
            raise serializers.ValidationError('Esta boleta ya tiene un pago registrado')
        if boleta.total < self.YAPE_MONTO_MINIMO:
            raise serializers.ValidationError(
                f'Yape requiere un monto mínimo de S/ {self.YAPE_MONTO_MINIMO}. '
                f'Total de la boleta: S/ {boleta.total}.'
            )
        self._boleta = boleta
        return value

    def validate_numero_celular(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('El celular debe contener solo dígitos')
        if not settings.DEBUG and not value.startswith('9'):
            raise serializers.ValidationError('Celular peruano: 9 dígitos, empieza con 9')
        return value
