from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdmin
from .models import Alerta
from .serializers import AlertaSerializer

@extend_schema(tags=['alertas'])
class AlertaListView(generics.ListAPIView):
    serializer_class = AlertaSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tipo', 'nivel', 'leida']

    def get_queryset(self):
        qs = Alerta.objects.select_related('producto')
        if 'leida' not in self.request.query_params:
            qs = qs.filter(leida=False)
        return qs

@extend_schema(tags=['alertas'], responses={200: AlertaSerializer})
class AlertaMarcarLeidaView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            alerta = Alerta.objects.get(pk=pk)
        except Alerta.DoesNotExist:
            return Response(
                {'detail': 'Alerta no encontrada', 'codigo': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        alerta.marcar_leida()
        return Response(AlertaSerializer(alerta).data)

@extend_schema(tags=['alertas'], responses={200: OpenApiTypes.OBJECT})
class AlertaMarcarTodasLeidasView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        tipo = request.data.get('tipo')
        qs = Alerta.objects.filter(leida=False)
        if tipo:
            qs = qs.filter(tipo=tipo)
        cantidad = qs.update(leida=True)
        return Response({'marcadas': cantidad})
