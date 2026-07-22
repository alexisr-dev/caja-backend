import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_inicializado = False

def _inicializar_firebase() -> bool:
    global _firebase_inicializado
    if _firebase_inicializado:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_inicializado = True
            return True

        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if not cred_path or not str(cred_path):
            logger.warning('FIREBASE_CREDENTIALS_PATH no configurado, FCM deshabilitado')
            return False

        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
        _firebase_inicializado = True
        logger.info('Firebase Admin inicializado')
        return True
    except FileNotFoundError:
        logger.error('serviceAccountKey.json no encontrado en %s', settings.FIREBASE_CREDENTIALS_PATH)
        return False
    except Exception as exc:
        logger.exception('Error inicializando Firebase: %s', exc)
        return False

def enviar_notificacion_push(
    usuario,
    titulo: str,
    cuerpo: str,
    data: dict[str, Any] | None = None,
) -> 'Notificacion | None':
    from .models import DispositivoFCM, Notificacion

    data = data or {}
    tipo = data.get('tipo', Notificacion.Tipo.SISTEMA)

    notif = Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        cuerpo=cuerpo,
        data=data,
    )

    if not _inicializar_firebase():
        return notif

    tokens = list(
        DispositivoFCM.objects
        .filter(usuario=usuario, activo=True)
        .values_list('token_fcm', flat=True)
    )
    if not tokens:
        logger.debug('Usuario %s sin dispositivos FCM activos', usuario.email)
        return notif

    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=titulo, body=cuerpo),
            data={k: str(v) for k, v in data.items()},
            tokens=tokens,
        )
        resp = messaging.send_each_for_multicast(message)

        for idx, r in enumerate(resp.responses):
            if not r.success:
                token_fallido = tokens[idx]
                _manejar_token_invalido(token_fallido, r.exception)

        logger.info(
            'FCM envio: %d exitosos, %d fallidos (usuario=%s)',
            resp.success_count, resp.failure_count, usuario.email,
        )
    except Exception as exc:
        logger.exception('Error enviando FCM a %s: %s', usuario.email, exc)

    return notif

def _manejar_token_invalido(token: str, exc: Exception | None) -> None:
    from .models import DispositivoFCM

    logger.info('Desactivando token FCM invalido: %s (motivo: %s)', token[:20], exc)

    DispositivoFCM.objects.filter(token_fcm=token).update(activo=False)
