from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DispositivoFCM, Notificacion
from .serializers import NotificacionSerializer, DispositivoFCMSerializer

@extend_schema(tags=['notificaciones'])
class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tipo', 'leida']

    def get_queryset(self):
        qs = Notificacion.objects.filter(usuario=self.request.user)
        leida_param = self.request.query_params.get('leida')
        if leida_param == 'false':
            qs = qs.filter(leida=False)
        elif leida_param == 'true':
            qs = qs.filter(leida=True)
        return qs

@extend_schema(tags=['notificaciones'])
class NotificacionMarcarLeidaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notificacion.objects.get(pk=pk, usuario=request.user)
        except Notificacion.DoesNotExist:
            return Response(
                {'detail': 'Notificación no encontrada', 'codigo': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        notif.marcar_leida()
        return Response(NotificacionSerializer(notif).data)

@extend_schema(tags=['notificaciones'])
class NotificacionMarcarTodasView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cantidad = Notificacion.objects.filter(
            usuario=request.user, leida=False,
        ).update(leida=True)
        return Response({'marcadas': cantidad})

@extend_schema(tags=['notificaciones'])
class DispositivoFCMCreateView(generics.CreateAPIView):
    serializer_class = DispositivoFCMSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(tags=['notificaciones'])
class DispositivoFCMDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DispositivoFCM.objects.filter(usuario=self.request.user)

    def destroy(self, request, *args, **kwargs):
        dispositivo = self.get_object()
        dispositivo.activo = False
        dispositivo.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)
