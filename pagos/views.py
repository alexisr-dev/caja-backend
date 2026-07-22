import hashlib
import hmac
import logging

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from users.permissions import IsAdminOrVendedor
from ventas.models import Boleta
from .models import Pago
from .serializers import (
    PagoSerializer,
    PagoEfectivoSerializer,
    PagoMPTarjetaSerializer,
    PagoMPYapeSerializer,
)

logger = logging.getLogger(__name__)


def _sanitizar_respuesta_mp(respuesta: dict) -> dict:
    """Filtra la respuesta de Mercado Pago para no persistir datos sensibles del pagador."""
    return {
        'id': respuesta.get('id'),
        'status': respuesta.get('status'),
        'status_detail': respuesta.get('status_detail'),
        'payment_method_id': respuesta.get('payment_method_id'),
        'currency_id': respuesta.get('currency_id'),
    }


class PagoThrottle(UserRateThrottle):
    scope = 'pago'

def _get_gateway_safe():
    from .gateways.mercadopago_gateway import get_gateway
    try:
        return get_gateway()
    except RuntimeError as exc:
        raise _GatewayNoDisponible(str(exc)) from exc

class _GatewayNoDisponible(Exception):
    pass

def _aprobar_boleta(boleta: Boleta, pago: Pago) -> None:
    boleta.asignar_numero()
    pago.estado = Pago.Estado.APROBADO
    pago.save(update_fields=['estado', 'actualizado'])
    boleta.estado = Boleta.Estado.PAGADA
    boleta.save(update_fields=['estado'])

def _build_error_response(resultado: dict, detalle_default: str) -> dict:
    return {
        'detail': detalle_default,
        'codigo': resultado.get('error', 'pago_rechazado'),
        'estado_mp': resultado.get('estado_mp', ''),
        'status_detail': resultado.get('status_detail', ''),
        'error_code': resultado.get('error_code'),
        'error_description': resultado.get('error_description'),
    }

@extend_schema(tags=['pagos'])
class PagoEfectivoView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def post(self, request):
        serializer = PagoEfectivoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        boleta = serializer._boleta

        with transaction.atomic():
            boleta.asignar_numero()

            pago = Pago.objects.create(
                boleta=boleta,
                metodo=Pago.Metodo.EFECTIVO,
                submetodo=Pago.Submetodo.NINGUNO,
                monto=boleta.total,
                monto_recibido=serializer.validated_data['monto_recibido'],
                estado=Pago.Estado.APROBADO,
            )
            boleta.estado = Boleta.Estado.PAGADA
            boleta.save(update_fields=['estado'])

        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['pagos'])
class PagoMPTarjetaView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PagoThrottle]

    def post(self, request):
        serializer = PagoMPTarjetaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        boleta = serializer._boleta
        data = serializer.validated_data

        try:
            gw = _get_gateway_safe()
        except _GatewayNoDisponible as exc:
            return Response(
                {'detail': str(exc), 'codigo': 'gateway_no_disponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            resultado = gw.cobrar_tarjeta(
                token_mp=data['token_mp'],
                monto=boleta.total,
                email_pagador=data['email_pagador'],
                cuotas=data['cuotas'],
                tipo_doc=data['tipo_doc'],
                num_doc=data['num_doc'],
                descripcion=f'Venta #{boleta.id} - Tienda',
                payment_method_id=data.get('payment_method_id', ''),
                issuer_id=data.get('issuer_id', ''),
            )
        except Exception as exc:
            logger.exception('Error inesperado llamando a MP tarjeta: %s', exc)
            return Response(
                {'detail': 'Error comunicándose con Mercado Pago', 'codigo': 'mp_error'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with transaction.atomic():
            Pago.objects.filter(boleta=boleta, estado=Pago.Estado.RECHAZADO).delete()

            if resultado['ok']:
                estado_pago = Pago.Estado.APROBADO
            elif resultado.get('pending'):
                estado_pago = Pago.Estado.PENDIENTE
            else:
                estado_pago = Pago.Estado.RECHAZADO

            pago = Pago.objects.create(
                boleta=boleta,
                metodo=Pago.Metodo.MERCADOPAGO,
                submetodo=Pago.Submetodo.TARJETA,
                monto=boleta.total,
                referencia_mp=resultado.get('referencia_mp', ''),
                respuesta_gateway=_sanitizar_respuesta_mp(resultado.get('respuesta', {})),
                estado=estado_pago,
            )
            if resultado['ok']:
                boleta.asignar_numero()
    
                boleta.estado = Boleta.Estado.PAGADA
                boleta.save(update_fields=['estado'])

        if resultado['ok']:
            return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)

        if resultado.get('pending'):
            return Response(
                {
                    'detail': 'Pago en proceso — se confirmará automáticamente',
                    'codigo': 'en_proceso',
                    'estado_mp': resultado.get('estado_mp', ''),
                    'status_detail': resultado.get('status_detail', ''),
                    'pago': PagoSerializer(pago).data,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        err = _build_error_response(resultado, 'Pago rechazado por Mercado Pago')
        err['pago'] = PagoSerializer(pago).data
        return Response(err, status=status.HTTP_402_PAYMENT_REQUIRED)

@extend_schema(tags=['pagos'])
class PagoMPYapeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PagoThrottle]

    def post(self, request):
        serializer = PagoMPYapeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        boleta = serializer._boleta
        data = serializer.validated_data

        try:
            gw = _get_gateway_safe()
        except _GatewayNoDisponible as exc:
            return Response(
                {'detail': str(exc), 'codigo': 'gateway_no_disponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            resultado = gw.cobrar_yape(
                numero_celular=data['numero_celular'],
                otp=data['otp'],
                monto=boleta.total,
                email_pagador=data['email_pagador'],
                descripcion=f'Venta #{boleta.id} - Tienda',
            )
        except Exception as exc:
            logger.exception('Error inesperado llamando a MP Yape: %s', exc)
            return Response(
                {'detail': 'Error comunicándose con Mercado Pago', 'codigo': 'mp_error'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with transaction.atomic():
            Pago.objects.filter(boleta=boleta, estado=Pago.Estado.RECHAZADO).delete()

            if resultado['ok']:
                estado_pago = Pago.Estado.APROBADO
            elif resultado.get('pending'):
                estado_pago = Pago.Estado.PENDIENTE
            else:
                estado_pago = Pago.Estado.RECHAZADO

            pago = Pago.objects.create(
                boleta=boleta,
                metodo=Pago.Metodo.MERCADOPAGO,
                submetodo=Pago.Submetodo.YAPE,
                monto=boleta.total,
                referencia_mp=resultado.get('referencia_mp', ''),
                respuesta_gateway=_sanitizar_respuesta_mp(resultado.get('respuesta', {})),
                estado=estado_pago,
            )
            if resultado['ok']:
                boleta.asignar_numero()
    
                boleta.estado = Boleta.Estado.PAGADA
                boleta.save(update_fields=['estado'])

        if resultado['ok']:
            return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)

        if resultado.get('pending'):
            return Response(
                {
                    'detail': 'Pago Yape en proceso — se confirmará automáticamente',
                    'codigo': 'en_proceso',
                    'estado_mp': resultado.get('estado_mp', ''),
                    'status_detail': resultado.get('status_detail', ''),
                    'pago': PagoSerializer(pago).data,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        err = _build_error_response(resultado, 'Pago Yape rechazado')
        err['pago'] = PagoSerializer(pago).data
        return Response(err, status=status.HTTP_402_PAYMENT_REQUIRED)

@extend_schema(tags=['pagos'])
class WebhookMPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.MP_WEBHOOK_SECRET:
            logger.error('Webhook MP: MP_WEBHOOK_SECRET no configurado — solicitud rechazada')
            return Response(
                {'detail': 'Webhook no disponible', 'codigo': 'configuracion_incompleta'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not self._validar_firma(request):
            logger.warning('Webhook MP: firma inválida desde %s', request.META.get('REMOTE_ADDR'))
            return Response(
                {'detail': 'Firma inválida', 'codigo': 'firma_invalida'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tipo = request.data.get('type') or request.query_params.get('type', '')
        if tipo != 'payment':
            return Response({'detail': 'Tipo ignorado'}, status=status.HTTP_200_OK)

        payment_id = (
            request.query_params.get('data.id', '')
            or str(request.data.get('data', {}).get('id', ''))
        )
        if not payment_id:
            return Response({'detail': 'Sin payment id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            gw = _get_gateway_safe()
            resultado = gw.consultar_pago(payment_id)
        except _GatewayNoDisponible:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            logger.exception('Webhook MP: error consultando pago %s: %s', payment_id, exc)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        pago = Pago.objects.select_related('boleta').filter(referencia_mp=payment_id).first()
        if not pago:
            logger.warning('Webhook MP: pago %s no encontrado en BD', payment_id)
            return Response(status=status.HTTP_200_OK)

        estado_mp = resultado.get('estado_mp', '')
        nuevo_estado = self._mapear_estado(estado_mp)

        if pago.estado == nuevo_estado:
            return Response(status=status.HTTP_200_OK)

        with transaction.atomic():
            pago.estado = nuevo_estado
            pago.respuesta_gateway = _sanitizar_respuesta_mp(resultado.get('respuesta', pago.respuesta_gateway))
            pago.save(update_fields=['estado', 'respuesta_gateway', 'actualizado'])

            boleta = pago.boleta
            if nuevo_estado == Pago.Estado.APROBADO and boleta.estado == Boleta.Estado.PENDIENTE:
                boleta.asignar_numero()
    
                boleta.estado = Boleta.Estado.PAGADA
                boleta.save(update_fields=['estado'])
            elif nuevo_estado == Pago.Estado.REEMBOLSADO and boleta.estado == Boleta.Estado.PAGADA:
                logger.info('Webhook MP: reembolso recibido para boleta %s', boleta.numero)

        return Response(status=status.HTTP_200_OK)

    @staticmethod
    def _mapear_estado(estado_mp: str) -> str:
        return {
            'approved':   Pago.Estado.APROBADO,
            'rejected':   Pago.Estado.RECHAZADO,
            'refunded':   Pago.Estado.REEMBOLSADO,
            'cancelled':  Pago.Estado.RECHAZADO,
        }.get(estado_mp, Pago.Estado.PENDIENTE)

    @staticmethod
    def _validar_firma(request) -> bool:
        x_signature = request.headers.get('x-signature', '')
        x_request_id = request.headers.get('x-request-id', '')

        ts = ''
        v1 = ''
        for part in x_signature.split(','):
            if part.startswith('ts='):
                ts = part[3:]
            elif part.startswith('v1='):
                v1 = part[3:]

        if not ts or not v1:
            return False

        payment_id = (
            request.query_params.get('data.id', '')
            or str(request.data.get('data', {}).get('id', ''))
        )
        template = f'id:{payment_id};request-date:{ts};'
        secret = settings.MP_WEBHOOK_SECRET.encode()
        esperado = hmac.new(secret, template.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(esperado, v1)

@extend_schema(tags=['pagos'])
class PagoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, boleta_id):
        try:
            pago = Pago.objects.select_related('boleta__cliente').get(boleta_id=boleta_id)
        except Pago.DoesNotExist:
            return Response(
                {'detail': 'Pago no encontrado para esta boleta', 'codigo': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user
        es_staff = getattr(user, 'es_admin', False) or getattr(user, 'es_vendedor', False)
        es_dueño = pago.boleta.cliente_id == user.pk

        if not es_staff and not es_dueño:
            return Response(
                {'detail': 'Sin permiso para ver este pago', 'codigo': 'forbidden'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(PagoSerializer(pago).data)
