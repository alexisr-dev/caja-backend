import logging
import uuid
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_MP_API = 'https://api.mercadopago.com'

_SAFE_RESPONSE_FIELDS = frozenset({
    'id', 'status', 'status_detail', 'date_approved', 'date_created',
    'payment_method_id', 'payment_type_id', 'installments',
    'transaction_amount', 'currency_id', 'description',
    'operation_type', 'authorization_code',
})

class MercadoPagoGateway:

    def __init__(self, access_token: str | None = None):
        token = access_token or settings.MP_ACCESS_TOKEN
        if not token:
            raise RuntimeError('MP_ACCESS_TOKEN no configurado. Defínelo en .env.')
        self._access_token = token

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json',
            'X-Idempotency-Key': str(uuid.uuid4()),
        }

    def cobrar_yape(
        self,
        numero_celular: str,
        otp: str,
        monto: Decimal,
        email_pagador: str,
        descripcion: str,
    ) -> dict[str, Any]:
        public_key = settings.MP_PUBLIC_KEY
        try:
            yape_resp = requests.post(
                f'{_MP_API}/platforms/pci/yape/v1/payment',
                params={'public_key': public_key},
                json={
                    'phoneNumber': numero_celular,
                    'otp': otp,
                    'requestId': str(uuid.uuid4()),
                },
                timeout=15,
            )
            yape_data = yape_resp.json()
        except requests.Timeout:
            logger.error('Yape token endpoint: timeout')
            return self._error('timeout', {})
        except requests.RequestException as exc:
            logger.exception('Yape token endpoint error: %s', exc)
            return self._error('yape_connection_error', {})

        logger.debug('Yape token response: HTTP %s | %s', yape_resp.status_code, str(yape_data)[:2000])

        if yape_resp.status_code not in (200, 201):
            logger.warning('Yape token rechazado: %s', yape_data)
            return self._error('token_invalido', yape_data)

        token_id = yape_data.get('id')
        if not token_id:
            logger.warning('Yape token sin id: %s', yape_data)
            return self._error('token_invalido', yape_data)

        return self._crear_pago({
            'transaction_amount': float(monto),
            'token': token_id,
            'description': descripcion,
            'installments': 1,
            'payment_method_id': 'yape',
            'payer': {'email': email_pagador},
        })

    def cobrar_tarjeta(
        self,
        token_mp: str,
        monto: Decimal,
        email_pagador: str,
        cuotas: int,
        tipo_doc: str,
        num_doc: str,
        descripcion: str,
        payment_method_id: str = '',
        issuer_id: str = '',
    ) -> dict[str, Any]:
        is_sandbox = self._access_token.startswith('TEST-')

        payer_data: dict[str, Any] = {'email': email_pagador}
        if not is_sandbox:
            payer_data['identification'] = {'type': tipo_doc, 'number': num_doc}

        body: dict[str, Any] = {
            'transaction_amount': float(monto),
            'token': token_mp,
            'description': descripcion,
            'installments': cuotas,
            'payer': payer_data,
        }
        if payment_method_id:
            body['payment_method_id'] = payment_method_id
        if issuer_id and not is_sandbox:
            body['issuer_id'] = int(issuer_id) if str(issuer_id).isdigit() else issuer_id
        return self._crear_pago(body)

    def consultar_pago(self, payment_id: str) -> dict[str, Any]:
        try:
            resp = requests.get(
                f'{_MP_API}/v1/payments/{payment_id}',
                headers=self._headers(),
                timeout=15,
            )
            data = resp.json()
        except requests.RequestException as exc:
            logger.exception('Error consultando pago %s: %s', payment_id, exc)
            return self._error('pago_no_encontrado', {})

        if resp.status_code not in (200, 201):
            return self._error('pago_no_encontrado', data)
        return self._parsear_respuesta_pago(data)

    def _crear_pago(self, body: dict) -> dict[str, Any]:
        token_preview = (body.get('token', '')[:8] + '…') if body.get('token') else '(none)'
        logger.debug(
            'MP /v1/payments → email=%s | method=%s | amount=%s | token=%s | installments=%s | issuer=%s',
            body.get('payer', {}).get('email', '?'),
            body.get('payment_method_id', '(none)'),
            body.get('transaction_amount'),
            token_preview,
            body.get('installments'),
            body.get('issuer_id', '(none)'),
        )

        try:
            resp = requests.post(
                f'{_MP_API}/v1/payments',
                headers=self._headers(),
                json=body,
                timeout=30,
            )
        except requests.Timeout:
            logger.error('MP /v1/payments timeout (30s)')
            return self._error('timeout', {})
        except requests.ConnectionError as exc:
            logger.error('MP /v1/payments connection error: %s', exc)
            return self._error('connection_error', {})
        except requests.RequestException as exc:
            logger.exception('MP /v1/payments error inesperado: %s', exc)
            return self._error('connection_error', {})

        logger.debug('MP /v1/payments ← HTTP %s | %s', resp.status_code, resp.text[:600])

        try:
            data = resp.json()
        except Exception:
            logger.error('MP respuesta no es JSON (HTTP %s): %s', resp.status_code, resp.text[:300])
            return self._error('invalid_response', {})

        if resp.status_code == 401:
            logger.error(
                'MP 401 Unauthorized — verifica que MP_ACCESS_TOKEN comience con TEST- '
                'y pertenezca a la misma app que MP_PUBLIC_KEY'
            )
            return self._error('credenciales_invalidas', data)

        if resp.status_code in (400, 403, 422):
            return self._clasificar_error_400(data, body)

        if resp.status_code >= 500:
            logger.error('MP 5xx server error (HTTP %s): %s', resp.status_code, data)
            return self._error('mp_server_error', data)

        if resp.status_code not in (200, 201):
            logger.warning('MP HTTP inesperado %s: %s', resp.status_code, data)
            return self._error('pago_rechazado', data)

        return self._parsear_respuesta_pago(data)

    def _clasificar_error_400(self, data: dict, body: dict) -> dict[str, Any]:
        cause_list = data.get('cause', [])
        if not isinstance(cause_list, list):
            cause_list = []

        cause_codes = [str(c.get('code', '')) for c in cause_list]
        logger.warning('MP 400/422 — causes: %s | full_response: %s', cause_codes, data)

        if '4390' in cause_codes:
            logger.warning(
                'Error 4390 payer_email_forbidden: email "%s" rechazado por MP. '
                'En Sandbox debes usar un email ficticio cualquiera (ej. '
                'comprador@example.com), NO el email de la cuenta MP dueña de la '
                'app NI un email test_user_*@testuser.com (esos están prohibidos '
                'como payer.email según docs oficiales de MP).',
                body.get('payer', {}).get('email', '?'),
            )
            return self._error('email_pagador_prohibido', data)

        if '3038' in cause_codes:
            logger.warning('Error 3038: token de tarjeta inválido o ya usado')
            return self._error('token_invalido', data)

        if '2067' in cause_codes:
            logger.warning('Error 2067: pago duplicado (idempotency)')
            return self._error('pago_duplicado', data)

        if '2041' in cause_codes:
            logger.error(
                'Error 2041 — GET to API APPLICATION fail.\n'
                '  Causas más comunes:\n'
                '  1. La app no tiene "Checkout API" habilitado como producto en el panel de MP.\n'
                '     Solución: Panel MP → Tu app → Editar → habilitar "Checkout API" → Guardar.\n'
                '  2. PUBLIC_KEY y ACCESS_TOKEN pertenecen a aplicaciones distintas.\n'
                '  3. issuer_id (%s) inválido en sandbox — ya se omite en modo TEST.',
                body.get('issuer_id', 'N/A'),
            )
            return self._error('app_no_configurada', data)

        return self._error('datos_invalidos', data)

    def _parsear_respuesta_pago(self, data: dict) -> dict[str, Any]:
        estado_mp = data.get('status', '')
        status_detail = data.get('status_detail', '')
        is_ok = estado_mp == 'approved'
        is_pending = estado_mp in ('pending', 'in_process', 'authorized')

        error_code: str | None = None
        error_description: str | None = None
        if not is_ok:
            causes = data.get('cause', [])
            if causes and isinstance(causes, list):
                error_code = str(causes[0].get('code', '')) or None
                error_description = causes[0].get('description') or None
            if not error_code and status_detail:
                error_code = status_detail

        safe_respuesta = {k: v for k, v in data.items() if k in _SAFE_RESPONSE_FIELDS}

        logger.info(
            'MP pago procesado: status=%s | detail=%s | id=%s | error_code=%s',
            estado_mp, status_detail, data.get('id'), error_code,
        )

        return {
            'ok': is_ok,
            'pending': is_pending,
            'estado_mp': estado_mp,
            'status_detail': status_detail,
            'referencia_mp': str(data.get('id', '')),
            'respuesta': safe_respuesta,
            'error': None if is_ok else ('en_proceso' if is_pending else 'no_aprobado'),
            'error_code': error_code,
            'error_description': error_description,
        }

    @staticmethod
    def _error(codigo: str, detalle: dict) -> dict[str, Any]:
        return {
            'ok': False,
            'pending': False,
            'estado_mp': '',
            'status_detail': '',
            'referencia_mp': '',
            'respuesta': {},
            'error': codigo,
            'error_code': None,
            'error_description': None,
        }

_singleton: MercadoPagoGateway | None = None

def get_gateway() -> MercadoPagoGateway:
    global _singleton
    if _singleton is None:
        _singleton = MercadoPagoGateway()
    return _singleton
