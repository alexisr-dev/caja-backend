from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

from .exceptions import (
    IAServiceBadRequest,
    IAServiceError,
    IAServiceImageTooLarge,
    IAServiceUnauthorized,
    IAServiceUnavailable,
)

logger = logging.getLogger(__name__)

class IAServiceClient:

    TIMEOUT_HEALTH = 3
    TIMEOUT_RECONOCER = 15
    TIMEOUT_REGISTRAR = 15
    TIMEOUT_DELETE = 10

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or settings.IA_SERVICE_URL).rstrip('/')
        self.api_key = api_key or settings.IA_SERVICE_API_KEY
        if not self.api_key:
            raise RuntimeError(
                'IA_SERVICE_API_KEY no configurado. Definelo en .env coincidiendo '
                'con el valor del .env de caja-ia-service.'
            )
        self._headers = {'X-API-Key': self.api_key}
        self._session = requests.Session()

    def health_check(self) -> bool:
        try:
            r = self._session.get(f'{self.base_url}/health', timeout=self.TIMEOUT_HEALTH)
            return r.status_code == 200 and r.json().get('status') == 'ok'
        except requests.RequestException as exc:
            logger.warning('IA service health check fallo: %s', exc)
            return False

    def reconocer(self, imagen_bytes: bytes, filename: str = 'frame.jpg') -> dict[str, Any]:
        files = {'imagen': (filename, imagen_bytes, 'image/jpeg')}
        try:
            r = self._session.post(
                f'{self.base_url}/reconocer',
                headers=self._headers,
                files=files,
                timeout=self.TIMEOUT_RECONOCER,
            )
        except requests.Timeout as exc:
            raise IAServiceUnavailable('Timeout en /reconocer') from exc
        except requests.ConnectionError as exc:
            raise IAServiceUnavailable('IA service no responde') from exc

        return self._procesar_response(r)

    def registrar_producto(self, imagen_bytes: bytes, id_chroma: str) -> dict[str, Any]:
        files = {'imagen': ('foto.jpg', imagen_bytes, 'image/jpeg')}
        data = {'id_chroma': id_chroma}
        try:
            r = self._session.post(
                f'{self.base_url}/registrar',
                headers=self._headers,
                files=files,
                data=data,
                timeout=self.TIMEOUT_REGISTRAR,
            )
        except requests.Timeout as exc:
            raise IAServiceUnavailable('Timeout en /registrar') from exc
        except requests.ConnectionError as exc:
            raise IAServiceUnavailable('IA service no responde') from exc

        return self._procesar_response(r)

    def eliminar_producto(self, id_chroma: str) -> dict[str, Any]:
        try:
            r = self._session.delete(
                f'{self.base_url}/producto/{id_chroma}',
                headers=self._headers,
                timeout=self.TIMEOUT_DELETE,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise IAServiceUnavailable(f'IA service no responde: {exc}') from exc

        return self._procesar_response(r)

    def stats_catalogo(self) -> dict[str, Any]:
        try:
            r = self._session.get(
                f'{self.base_url}/catalogo/stats',
                headers=self._headers,
                timeout=self.TIMEOUT_HEALTH,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise IAServiceUnavailable(f'IA service no responde: {exc}') from exc

        return self._procesar_response(r)

    @staticmethod
    def _procesar_response(r: requests.Response) -> dict[str, Any]:
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            raise IAServiceUnauthorized(
                'API key invalida — revisar IA_SERVICE_API_KEY en backend y ia-service'
            )
        if r.status_code == 413:
            raise IAServiceImageTooLarge(
                f'Imagen muy grande para el IA service: {r.json().get("detail")}'
            )
        if r.status_code == 503:
            raise IAServiceUnavailable(
                f'IA service no listo: {r.json().get("detail", "modelos cargando")}'
            )
        if 400 <= r.status_code < 500:
            raise IAServiceBadRequest(f'{r.status_code}: {r.text[:200]}')

        raise IAServiceError(f'Error inesperado del IA service: {r.status_code}')

_singleton: IAServiceClient | None = None

def get_client() -> IAServiceClient:
    global _singleton
    if _singleton is None:
        _singleton = IAServiceClient()
    return _singleton
