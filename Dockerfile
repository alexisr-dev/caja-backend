# Imagen base ligera de Python
FROM python:3.12-slim

# Evita archivos .pyc y fuerza salida sin buffer (logs en tiempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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

EXPOSE 8000

# Arranque por defecto (el compose lo sobrescribe en desarrollo)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
