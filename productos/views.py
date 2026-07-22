import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdmin, IsAdminOrVendedor
from .models import (
    Categoria, Proveedor, Producto,
    FotoProducto, HistorialPrecio, Descuento,
    Favorito, MovimientoStock,
)
from .serializers import (
    CategoriaSerializer,
    ProveedorSerializer,
    ProductoListSerializer,
    ProductoDetailSerializer,
    ProductoWriteSerializer,
    FotoProductoSerializer,
    HistorialPrecioSerializer,
    AjusteStockSerializer,
    MovimientoStockSerializer,
    DescuentoSerializer,
    FavoritoSerializer,
)

logger = logging.getLogger(__name__)

@extend_schema(tags=['productos'])
class CategoriaListCreateView(generics.ListCreateAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdmin()]

@extend_schema(tags=['productos'])
class CategoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdmin]

@extend_schema(tags=['productos'])
class ProveedorListCreateView(generics.ListCreateAPIView):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['razon_social', 'ruc']

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdminOrVendedor()]
        return [IsAdmin()]

@extend_schema(tags=['productos'])
class ProveedorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAdmin]

@extend_schema(tags=['productos'])
class ProductoListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'activo', 'padre']
    search_fields = ['nombre', 'sku', 'descripcion']
    ordering_fields = ['nombre', 'precio', 'stock', 'contador_ventas', 'creado']
    ordering = ['nombre']

    def get_queryset(self):
        qs = Producto.objects.select_related('categoria', 'proveedor').prefetch_related('fotos')
        user = self.request.user
        if hasattr(user, 'es_cliente') and user.es_cliente:
            qs = qs.filter(activo=True)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductoWriteSerializer
        return ProductoListSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdmin()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        return Response(
            ProductoDetailSerializer(producto).data,
            status=status.HTTP_201_CREATED,
        )

@extend_schema(tags=['productos'])
class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Producto.objects.select_related('categoria', 'proveedor', 'padre').prefetch_related(
        'fotos', 'descuentos', 'variantes',
    )
    lookup_field = 'sku'

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return ProductoWriteSerializer
        return ProductoDetailSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdmin()]

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        return Response(ProductoDetailSerializer(producto).data)

    def destroy(self, request, *args, **kwargs):
        producto = self.get_object()
        producto.activo = False
        producto.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=['productos'])
class ProductoHistorialPreciosView(generics.ListAPIView):
    serializer_class = HistorialPrecioSerializer
    permission_classes = [IsAdminOrVendedor]

    def get_queryset(self):
        sku = self.kwargs['sku']
        get_object_or_404(Producto, sku=sku)
        return HistorialPrecio.objects.filter(producto_id=sku).select_related('usuario')

@extend_schema(tags=['productos'])
class ProductoAjusteStockView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def post(self, request, sku):
        producto = get_object_or_404(Producto, sku=sku)
        serializer = AjusteStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo = serializer.validated_data['tipo']
        cantidad = serializer.validated_data['cantidad']
        motivo = serializer.validated_data.get('motivo', '')

        with transaction.atomic():
            if tipo == MovimientoStock.Tipo.ENTRADA:
                producto.stock += cantidad
            else:
                producto.stock += cantidad
                if producto.stock < 0:
                    return Response(
                        {'detail': 'El ajuste dejaria stock negativo', 'codigo': 'stock_negativo'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            producto.save(update_fields=['stock'])

            movimiento = MovimientoStock.objects.create(
                producto=producto,
                tipo=tipo,
                cantidad=cantidad,
                usuario=request.user,
                motivo=motivo,
            )

        return Response({
            'stock_actual': producto.stock,
            'movimiento': MovimientoStockSerializer(movimiento).data,
        })

@extend_schema(tags=['productos'])
class FotoProductoCreateView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, sku):
        producto = get_object_or_404(Producto, sku=sku)
        serializer = FotoProductoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        foto = serializer.save(producto=producto)
        return Response(FotoProductoSerializer(foto).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['productos'])
class FotoProductoDeleteView(generics.DestroyAPIView):
    queryset = FotoProducto.objects.all()
    serializer_class = FotoProductoSerializer
    permission_classes = [IsAdmin]

@extend_schema(tags=['descuentos'])
class DescuentoListCreateView(generics.ListCreateAPIView):
    serializer_class = DescuentoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['producto', 'tipo', 'activo']

    def get_queryset(self):
        return Descuento.objects.select_related('producto')

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdminOrVendedor()]
        return [IsAdmin()]

@extend_schema(tags=['descuentos'])
class DescuentoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Descuento.objects.all()
    serializer_class = DescuentoSerializer
    permission_classes = [IsAdmin]

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

@extend_schema(tags=['favoritos'])
class FavoritoListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorito.objects.filter(
            cliente=self.request.user,
        ).select_related('producto__categoria')

    def perform_create(self, serializer):
        serializer.save(cliente=self.request.user)

@extend_schema(tags=['favoritos'])
class FavoritoDeleteView(generics.DestroyAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorito.objects.filter(cliente=self.request.user)
