# Imagen base ligera de Python
FROM python:3.12-slim

# Evita archivos .pyc y fuerza salida sin buffer (logs en tiempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings.production

WORKDIR /app

# Dependencias de sistema minimas (para Pillow/psycopg y compilaciones puntuales)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias de Python primero (mejor cache de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia el resto del codigo
COPY . .

# Genera los estaticos (los sirve WhiteNoise en runtime).
# Los valores dummy son obligatorios: settings/base.py lee SECRET_KEY y DB_*
# sin default, asi que importar los settings falla sin ellos. collectstatic
# no toca la base de datos, solo necesita que las variables existan.
RUN SECRET_KEY=build-only \
    DB_NAME=build DB_USER=build DB_PASSWORD=build \
    SECURE_SSL_REDIRECT=False \
    python manage.py collectstatic --noinput

# Usuario sin privilegios
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Arranque de produccion (el compose de desarrollo lo sobrescribe con runserver)
CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
