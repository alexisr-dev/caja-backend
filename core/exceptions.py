import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, list):
            response.data = {'detail': response.data, 'codigo': 'validation_error'}
        elif isinstance(response.data, dict) and 'detail' not in response.data:
            response.data = {
                'detail': 'Error de validacion',
                'codigo': 'validation_error',
                'campos': response.data,
            }
        elif isinstance(response.data, dict) and 'codigo' not in response.data:
            response.data['codigo'] = _codigo_por_status(response.status_code)
        return response

    if isinstance(exc, IntegrityError):
        logger.warning('IntegrityError: %s', exc)
        return Response(
            {
                'detail': 'Conflicto: violacion de restriccion de integridad',
                'codigo': 'integrity_error',
            },
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, DjangoValidationError):
        campos = exc.message_dict if hasattr(exc, 'message_dict') else None
        return Response(
            {
                'detail': 'Error de validacion',
                'codigo': 'validation_error',
                'campos': campos or {'__all__': exc.messages},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger.exception('Excepcion no manejada en %s: %s', context.get('view'), exc)
    return None

def _codigo_por_status(http_status: int) -> str:
    return {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        413: 'payload_too_large',
        429: 'rate_limited',
    }.get(http_status, 'error')
