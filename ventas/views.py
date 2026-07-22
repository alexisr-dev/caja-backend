import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdmin, IsAdminOrVendedor
from .models import Boleta, CarritoPersistente, ItemCarrito
from .serializers import (
    BoletaListSerializer,
    BoletaDetailSerializer,
    BoletaCreateSerializer,
    BoletaAnularSerializer,
    CarritoSerializer,
    ItemCarritoSerializer,
    ItemCarritoWriteSerializer,
    ItemCarritoCantidadSerializer,
)

logger = logging.getLogger(__name__)

@extend_schema(tags=['boletas'])
class BoletaListCreateView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdminOrVendedor()]
        return [IsAuthenticated()]

    def get(self, request):
        qs = Boleta.objects.select_related('cliente', 'vendedor')

        if not getattr(request.user, 'es_admin', False):
            qs = qs.filter(vendedor=request.user)

        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        turno = request.query_params.get('turno')
        if turno:
            qs = qs.filter(turno_id=turno)
        fecha_desde = request.query_params.get('fecha_desde')
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        fecha_hasta = request.query_params.get('fecha_hasta')
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)

        from core.pagination import StandardPagination
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = BoletaListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = BoletaCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        boleta = serializer.save()
        return Response(BoletaDetailSerializer(boleta).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['boletas'])
class BoletaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        boleta = get_object_or_404(
            Boleta.objects.select_related('cliente', 'vendedor', 'turno').prefetch_related('detalles__producto'),
            pk=pk,
        )
        user = request.user
        es_staff = getattr(user, 'es_admin', False) or getattr(user, 'es_vendedor', False)
        es_dueño = boleta.cliente_id == user.pk

        if not es_staff and not es_dueño:
            return Response(
                {'detail': 'No tienes permiso para ver esta boleta.', 'codigo': 'forbidden'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(BoletaDetailSerializer(boleta, context={'request': request}).data)

@extend_schema(tags=['boletas'])
class BoletaCancelarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        boleta = get_object_or_404(Boleta, pk=pk)
        user = request.user
        es_staff = getattr(user, 'es_admin', False) or getattr(user, 'es_vendedor', False)
        es_dueño = boleta.cliente_id == user.pk

        if not es_staff and not es_dueño:
            return Response(
                {'detail': 'No tienes permiso para cancelar esta boleta.', 'codigo': 'forbidden'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if boleta.estado != Boleta.Estado.PENDIENTE:
            return Response(
                {'detail': f'Solo se pueden cancelar boletas PENDIENTE (estado actual: {boleta.estado}).',
                 'codigo': 'estado_invalido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motivo = 'Cancelada por el vendedor (venta no completada)' if es_staff \
            else 'Cancelada por el cliente (compra abandonada)'

        boleta.estado = Boleta.Estado.ANULADA
        boleta.anulada_fecha = timezone.now()
        boleta.anulada_por = request.user
        boleta.anulada_motivo = motivo
        boleta.save()

        return Response(BoletaDetailSerializer(boleta).data)

@extend_schema(tags=['boletas'])
class BoletaAnularView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def post(self, request, pk):
        boleta = get_object_or_404(Boleta, pk=pk)

        if boleta.estado != Boleta.Estado.PAGADA:
            return Response(
                {'detail': f'Solo se pueden anular boletas PAGADAS (estado actual: {boleta.estado}).',
                 'codigo': 'estado_invalido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BoletaAnularSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        boleta.estado = Boleta.Estado.ANULADA
        boleta.anulada_fecha = timezone.now()
        boleta.anulada_por = request.user
        boleta.anulada_motivo = serializer.validated_data.get('motivo', '')
        boleta.save()

        return Response(BoletaDetailSerializer(boleta).data)

@extend_schema(tags=['boletas'])
class MisBoletasView(generics.ListAPIView):
    serializer_class = BoletaListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['estado']
    ordering = ['-fecha']

    def get_queryset(self):
        return Boleta.objects.filter(
            cliente=self.request.user,
        ).select_related('vendedor')

@extend_schema(tags=['carrito'])
class CarritoView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_or_create_carrito(self, user):
        carrito, _ = CarritoPersistente.objects.get_or_create(cliente=user)
        return carrito

    def get(self, request):
        carrito = self._get_or_create_carrito(request.user)
        return Response(CarritoSerializer(carrito).data)

    def delete(self, request):
        carrito = self._get_or_create_carrito(request.user)
        carrito.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=['carrito'])
class ItemCarritoCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ItemCarritoWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku = serializer.validated_data['sku']
        cantidad = serializer.validated_data['cantidad']
        producto = serializer._producto

        carrito, _ = CarritoPersistente.objects.get_or_create(cliente=request.user)

        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={'cantidad': cantidad},
        )
        if not created:
            item.cantidad = cantidad
            item.save(update_fields=['cantidad'])

        return Response(
            ItemCarritoSerializer(item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

@extend_schema(tags=['carrito'])
class ItemCarritoUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        item = get_object_or_404(ItemCarrito, pk=pk, carrito__cliente=request.user)
        serializer = ItemCarritoCantidadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.cantidad = serializer.validated_data['cantidad']
        item.save(update_fields=['cantidad'])
        return Response(ItemCarritoSerializer(item).data)

@extend_schema(tags=['carrito'])
class ItemCarritoDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        item = get_object_or_404(ItemCarrito, pk=pk, carrito__cliente=request.user)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
