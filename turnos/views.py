from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminOrVendedor
from .models import TurnoCaja
from .serializers import TurnoSerializer, TurnoAbrirSerializer, TurnoCerrarSerializer

@extend_schema(tags=['turnos'])
class TurnoAbrirView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def post(self, request):
        if TurnoCaja.objects.filter(vendedor=request.user, estado=TurnoCaja.Estado.ABIERTO).exists():
            return Response(
                {'detail': 'Ya tienes un turno abierto. Ciérralo antes de abrir uno nuevo.',
                 'codigo': 'turno_ya_abierto'},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = TurnoAbrirSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        turno = TurnoCaja.objects.create(
            vendedor=request.user,
            monto_inicial=serializer.validated_data['monto_inicial'],
            estado=TurnoCaja.Estado.ABIERTO,
        )
        return Response(TurnoSerializer(turno).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['turnos'])
class TurnoCerrarView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def post(self, request):
        turno = TurnoCaja.objects.filter(
            vendedor=request.user, estado=TurnoCaja.Estado.ABIERTO,
        ).first()
        if not turno:
            return Response(
                {'detail': 'No tienes un turno abierto actualmente.', 'codigo': 'sin_turno_activo'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TurnoCerrarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        turno.estado = TurnoCaja.Estado.CERRADO
        turno.cierre_fecha = timezone.now()
        turno.monto_contado_cierre = serializer.validated_data['monto_contado_cierre']
        turno.observaciones = serializer.validated_data.get('observaciones', '')
        turno.save()

        return Response(TurnoSerializer(turno).data)

@extend_schema(
    tags=['turnos'],
    responses={200: TurnoSerializer, 204: None},
)
class TurnoActivoView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def get(self, request):
        turno = TurnoCaja.objects.filter(
            vendedor=request.user, estado=TurnoCaja.Estado.ABIERTO,
        ).first()
        if not turno:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(TurnoSerializer(turno).data)

@extend_schema(tags=['turnos'])
class TurnoListView(generics.ListAPIView):
    serializer_class = TurnoSerializer
    permission_classes = [IsAdminOrVendedor]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['estado', 'vendedor']
    ordering_fields = ['apertura_fecha', 'cierre_fecha']
    ordering = ['-apertura_fecha']

    def get_queryset(self):
        user = self.request.user
        qs = TurnoCaja.objects.select_related('vendedor')
        if getattr(user, 'es_admin', False):
            return qs
        return qs.filter(vendedor=user)

@extend_schema(tags=['turnos'])
class TurnoDetailView(generics.RetrieveAPIView):
    serializer_class = TurnoSerializer
    permission_classes = [IsAdminOrVendedor]

    def get_queryset(self):
        user = self.request.user
        qs = TurnoCaja.objects.select_related('vendedor')
        if getattr(user, 'es_admin', False):
            return qs
        return qs.filter(vendedor=user)
