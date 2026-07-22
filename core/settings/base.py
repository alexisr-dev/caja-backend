from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='localhost,127.0.0.1')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
]

LOCAL_APPS = [
    'users',
    'productos',
    'ventas',
    'pagos',
    'turnos',
    'alertas',
    'notificaciones',
    'ia_service',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_USER_MODEL = 'users.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_RATES': {
        'pago':       '10/minute',
        'login':      '10/minute',
        'otp_send':   '3/minute',
        'otp_verify': '5/minute',
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Caja Backend API',
    'DESCRIPTION': (
        'API REST del sistema de caja inteligente.\n\n'
        '**Autenticacion:** Bearer JWT (access token).\n'
        'Obtener tokens en `POST /api/auth/login/`.\n\n'
        '**Roles:**\n'
        '- `ADMIN` — acceso total\n'
        '- `VENDEDOR` — caja, turnos, boletas, productos (lectura)\n'
        '- `CLIENTE` — carrito, mis-boletas, favoritos, reseñas\n'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,

    'SECURITY': [{'BearerAuth': []}],
    'COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },

    'TAGS': [
        {'name': 'auth',           'description': 'Autenticacion, registro, 2FA, perfil'},
        {'name': 'productos',      'description': 'Catalogo, stock, historial de precios'},
        {'name': 'descuentos',     'description': 'Descuentos por producto'},
        {'name': 'favoritos',      'description': 'Favoritos del cliente'},
        {'name': 'resenas',        'description': 'Reseñas de productos'},
        {'name': 'turnos',         'description': 'Turnos de caja (apertura/cierre)'},
        {'name': 'boletas',        'description': 'Boletas de venta'},
        {'name': 'carrito',        'description': 'Carrito persistente del cliente'},
        {'name': 'pagos',          'description': 'Efectivo, Mercado Pago, webhook'},
        {'name': 'alertas',        'description': 'Alertas de stock y sistema'},
        {'name': 'notificaciones', 'description': 'Push notifications y dispositivos FCM'},
        {'name': 'ia',             'description': 'Reconocimiento de productos por imagen'},
        {'name': 'reportes',       'description': 'Dashboard y reportes de negocio'},
    ],

    'ENUM_GENERATE_CHOICE_DESCRIPTION': True,

    'SORT_OPERATIONS': True,

    'PREPROCESSING_HOOKS': [
        'drf_spectacular.hooks.preprocess_exclude_path_format',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('JWT_ACCESS_LIFETIME_MINUTES', cast=int, default=15)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('JWT_REFRESH_LIFETIME_DAYS', cast=int, default=7)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ISSUER': config('JWT_ISSUER', default='caja-backend'),
    'AUDIENCE': config('JWT_AUDIENCE', default='caja-frontend'),
}

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    cast=Csv(),
    default='http://localhost:5173',
)
CORS_ALLOW_CREDENTIALS = True

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@localhost')

MP_PUBLIC_KEY = config('MP_PUBLIC_KEY', default='')
MP_ACCESS_TOKEN = config('MP_ACCESS_TOKEN', default='')
MP_WEBHOOK_SECRET = config('MP_WEBHOOK_SECRET', default='')

FIREBASE_CREDENTIALS_PATH = BASE_DIR / config(
    'FIREBASE_CREDENTIALS_PATH',
    default='firebase/serviceAccountKey.json',
)

GOOGLE_OAUTH_CLIENT_IDS = config(
    'GOOGLE_OAUTH_CLIENT_IDS',
    cast=Csv(),
    default='',
)

IA_SERVICE_URL = config('IA_SERVICE_URL', default='http://localhost:8001')
IA_SERVICE_API_KEY = config('IA_SERVICE_API_KEY', default='')

IGV_PORCENTAJE = config('IGV_PORCENTAJE', cast=float, default=0.18)
