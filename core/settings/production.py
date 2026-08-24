from decouple import config, Csv

from .base import *

DEBUG = False

# Dominio publico del despliegue. Se usa como base para ALLOWED_HOSTS y
# CSRF_TRUSTED_ORIGINS para no depender de que el .env del VPS los traiga.
SITE_DOMAIN = config('SITE_DOMAIN', default='caja.alexissramirez.com')

ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, SITE_DOMAIN]))

# Nginx/Cloudflare terminan el TLS: sin esto Django ve http y descarta la
# cookie de sesion marcada como Secure (la sesion del admin no persiste).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Configurable por entorno: detras de Nginx/Caddy con HTTPS va en True,
# pero en pruebas locales sin TLS hay que apagarlo para evitar el bucle de 301.
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', cast=bool, default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_DOMAIN se deja sin definir a proposito: Django usa el host de
# la peticion. Fijarlo a mano rompe la sesion si el host no coincide exacto.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Necesario para que el login del admin funcione detras del proxy inverso
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([
    f'https://{SITE_DOMAIN}',
    *config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default=''),
]))

# WhiteNoise sirve /static/ desde el propio contenedor (el admin necesita CSS).
# Ojo: no sirve /media/, eso lo tiene que servir Nginx desde el volumen.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'pagos': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
