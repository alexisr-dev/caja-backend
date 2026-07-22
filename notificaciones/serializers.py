from rest_framework import serializers

from .models import DispositivoFCM, Notificacion

class NotificacionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Notificacion
        fields = ('id', 'tipo', 'tipo_display', 'titulo', 'cuerpo', 'data', 'leida', 'fecha_envio')
        read_only_fields = fields

class DispositivoFCMSerializer(serializers.ModelSerializer):

    class Meta:
        model = DispositivoFCM
        fields = ('id', 'token_fcm', 'plataforma', 'activo', 'registrado')
        read_only_fields = ('id', 'activo', 'registrado')

    def create(self, validated_data):
        obj, _ = DispositivoFCM.objects.update_or_create(
            token_fcm=validated_data['token_fcm'],
            defaults={
                'usuario': self.context['request'].user,
                'plataforma': validated_data['plataforma'],
                'activo': True,
            },
        )
        return obj
