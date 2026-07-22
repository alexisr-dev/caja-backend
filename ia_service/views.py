import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, filters
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from productos.models import Producto
from productos.serializers import ProductoDetailSerializer
from users.permissions import IsAdmin, IsAdminOrVendedor
from .client import get_client
from .exceptions import (
    IAServiceError,
    IAServiceUnavailable,
    IAServiceImageTooLarge,
    IAServiceBadRequest,
)
from .models import LogEscaneoIA
from .serializers import EscanearSerializer, RegistroVisualSerializer, LogEscaneoSerializer

logger = logging.getLogger(__name__)

_RESULTADO_MAP = {
    'ok':                  LogEscaneoIA.Resultado.OK,
    'no_detectado':        LogEscaneoIA.Resultado.NO_DETECTADO,
    'producto_desconocido': LogEscaneoIA.Resultado.DESCONOCIDO,
    'catalogo_vacio':      LogEscaneoIA.Resultado.NO_DETECTADO,
}

def _get_ia_client_safe():
    try:
        return get_client()
    except RuntimeError as exc:
        raise IAServiceUnavailable(str(exc)) from exc

@extend_schema(
    tags=['ia'],
    request=EscanearSerializer,
    responses={200: LogEscaneoSerializer},
)
class EscanearView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = EscanearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        imagen = serializer.validated_data['imagen']
        imagen_bytes = imagen.read()

        modo = (
            LogEscaneoIA.Modo.MOVIL
            if getattr(request.user, 'es_cliente', False)
            else LogEscaneoIA.Modo.CAJA
        )

        resultado_log = LogEscaneoIA.Resultado.ERROR
        producto_obj = None
        ia_data = {}

        try:
            client = _get_ia_client_safe()
            ia_data = client.reconocer(imagen_bytes, filename=imagen.name or 'frame.jpg')
        except IAServiceImageTooLarge:
            return Response(
                {'detail': 'Imagen demasiado grande (max 5 MB)', 'codigo': 'imagen_muy_grande'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        except IAServiceUnavailable as exc:
            LogEscaneoIA.objects.create(
                usuario=request.user,
                modo=modo,
                resultado=LogEscaneoIA.Resultado.ERROR,
            )
            logger.error('IA service no disponible: %s', exc)
            return Response(
                {'detail': 'Servicio de reconocimiento no disponible', 'codigo': 'ia_no_disponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except IAServiceError as exc:
            LogEscaneoIA.objects.create(
                usuario=request.user,
                modo=modo,
                resultado=LogEscaneoIA.Resultado.ERROR,
            )
            logger.error('Error IA service: %s', exc)
            return Response(
                {'detail': 'Error en el servicio de reconocimiento', 'codigo': 'ia_error'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        resultado_ia = ia_data.get('resultado', 'no_detectado')
        resultado_log = _RESULTADO_MAP.get(resultado_ia, LogEscaneoIA.Resultado.ERROR)
        confianza = ia_data.get('confianza')
        latencia_ms = ia_data.get('latencia_ms')

        if resultado_ia == 'ok':
            sku = ia_data.get('sku')
            try:
                producto_obj = Producto.objects.select_related(
                    'categoria', 'proveedor',
                ).prefetch_related('fotos', 'descuentos', 'variantes').get(sku=sku)
            except Producto.DoesNotExist:
                resultado_log = LogEscaneoIA.Resultado.SKU_NO_EXISTE
                logger.warning('IA devolvio SKU %s que no existe en BD', sku)

        LogEscaneoIA.objects.create(
            usuario=request.user,
            modo=modo,
            producto_detectado=producto_obj,
            resultado=resultado_log,
            confianza=confianza,
            latencia_ms=latencia_ms,
        )

        response_data = {
            'resultado': resultado_log,
            'confianza': confianza,
            'latencia_ms': latencia_ms,
        }
        if ia_data.get('bbox'):
            response_data['bbox'] = ia_data['bbox']
        if producto_obj:
            response_data['producto'] = ProductoDetailSerializer(producto_obj).data

        return Response(response_data)

@extend_schema(
    tags=['ia'],
    request=RegistroVisualSerializer,
    responses={201: LogEscaneoSerializer},
)
class RegistroVisualView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = RegistroVisualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku = serializer.validated_data['sku']
        sufijo = serializer.validated_data['sufijo']
        imagen = serializer.validated_data['imagen']
        imagen_bytes = imagen.read()
        id_chroma = f'{sku}_{sufijo}'

        try:
            client = _get_ia_client_safe()
            result = client.registrar_producto(imagen_bytes, id_chroma)
        except IAServiceImageTooLarge:
            return Response(
                {'detail': 'Imagen demasiado grande (max 5 MB)', 'codigo': 'imagen_muy_grande'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        except IAServiceUnavailable as exc:
            logger.error('IA service no disponible en registro-visual: %s', exc)
            return Response(
                {'detail': 'Servicio IA no disponible', 'codigo': 'ia_no_disponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except IAServiceBadRequest as exc:
            return Response(
                {'detail': str(exc), 'codigo': 'ia_bad_request'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IAServiceError as exc:
            logger.error('Error IA service en registro-visual: %s', exc)
            return Response(
                {'detail': 'Error en el servicio IA', 'codigo': 'ia_error'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            'id_chroma': id_chroma,
            'sku': sku,
            'ia_response': result,
        }, status=status.HTTP_201_CREATED)

@extend_schema(tags=['ia'])
class LogEscaneoListView(generics.ListAPIView):
    serializer_class = LogEscaneoSerializer
    permission_classes = [IsAdminOrVendedor]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['resultado', 'modo']
    ordering_fields = ['fecha', 'latencia_ms']
    ordering = ['-fecha']

    def get_queryset(self):
        qs = LogEscaneoIA.objects.select_related('usuario', 'producto_detectado')

        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)
        return qs

@extend_schema(tags=['ia'])
class IAHealthView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        try:
            client = _get_ia_client_safe()
            ok = client.health_check()
        except IAServiceError:
            ok = False

        if ok:
            return Response({'status': 'ok'})
        return Response(
            {'status': 'down', 'detail': 'IA service no responde'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

@extend_schema(tags=['ia'])
class IACatalogoStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        try:
            client = _get_ia_client_safe()
            stats = client.stats_catalogo()
        except IAServiceUnavailable as exc:
            return Response(
                {'detail': str(exc), 'codigo': 'ia_no_disponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except IAServiceError as exc:
            return Response(
                {'detail': str(exc), 'codigo': 'ia_error'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(stats)
