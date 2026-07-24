<div align="center">

# 🛒 Caja Backend

### API REST para un sistema de caja inteligente de supermercado

Backend robusto construido con **Django REST Framework** que gestiona ventas, inventario,
pagos digitales, turnos de caja y reconocimiento de productos por imagen — con autenticación
JWT, 2FA y control de acceso por roles.

<br>

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.17-A30000?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=for-the-badge)

</div>

---

## 📑 Tabla de contenidos

- [✨ Características](#-características)
- [📸 Capturas de pantalla](#-capturas-de-pantalla)
- [🚀 Tecnologías utilizadas](#-tecnologías-utilizadas)
- [📦 Instalación](#-instalación)
- [⚙️ Configuración](#️-configuración)
- [▶️ Uso](#️-uso)
- [📁 Estructura del proyecto](#-estructura-del-proyecto)
- [🔌 API](#-api)
- [🧪 Testing](#-testing)
- [📈 Roadmap](#-roadmap)
- [🤝 Contribuciones](#-contribuciones)
- [📄 Licencia](#-licencia)
- [👤 Autor](#-autor)
- [⭐ Agradecimientos](#-agradecimientos)

---

## ✨ Características

- 🔐 **Autenticación JWT** con *access* / *refresh tokens*, rotación y *blacklist* al cerrar sesión.
- 📧 **Verificación en dos pasos (2FA)** por email y **recuperación de contraseña** con códigos temporales *hasheados*.
- 🔑 **Google Sign-In** (OAuth) además del registro tradicional.
- 👥 **Control de acceso por roles**: `ADMIN`, `VENDEDOR` y `CLIENTE`.
- 📦 **Catálogo de productos** con SKU, categorías, proveedores, control de stock, historial de precios y fotos.
- ❤️ **Favoritos** y **carrito persistente** por cliente.
- 🧾 **Boletas de venta** con cancelación y anulación.
- 🕒 **Turnos de caja** (apertura / cierre con arqueo).
- 💳 **Pagos**: efectivo, **Mercado Pago** (tarjeta y **Yape**) y *webhook* de confirmación.
- 🔔 **Alertas de stock** y **notificaciones push** vía Firebase Cloud Messaging (FCM).
- 🤖 **Reconocimiento de productos por imagen** (microservicio de IA vía HTTP).
- 📊 **Reportes y dashboard**: ventas, top de productos, stock bajo y tasa de acierto de IA.
- 🛡️ **Throttling** en endpoints sensibles (login, OTP, pagos).
- 📖 **Documentación OpenAPI** interactiva con Swagger UI y Redoc.
- 🐳 **Listo para Docker** — levanta backend + base de datos con un comando.

---

## 📸 Capturas de pantalla

> _Espacio para imágenes o GIFs del proyecto en funcionamiento._

| Swagger UI | Panel de administración |
|:---:|:---:|
| ![Swagger UI](docs/img/swagger.png) | ![Admin](docs/img/admin.png) |

`<Completar: agregar capturas reales en docs/img/>`

---

## 🚀 Tecnologías utilizadas

| Tecnología | Uso |
|------------|-----|
| **Django 5.1** | Framework web principal |
| **Django REST Framework** | Construcción de la API REST |
| **SimpleJWT** | Autenticación con tokens JWT (+ blacklist) |
| **PostgreSQL 16** | Base de datos relacional |
| **drf-spectacular** | Generación de esquema OpenAPI / Swagger / Redoc |
| **django-cors-headers** | Manejo de CORS para el frontend |
| **django-filter** | Filtrado, búsqueda y ordenamiento en endpoints |
| **Pillow** | Procesamiento de imágenes de productos |
| **ReportLab** | Generación de documentos PDF (boletas) |
| **mercadopago** | Integración de pagos (tarjeta / Yape) |
| **firebase-admin** | Notificaciones push (FCM) |
| **google-auth** | Verificación de Google Sign-In |
| **python-decouple** | Gestión de variables de entorno |
| **Docker + Docker Compose** | Contenerización y orquestación local |

---

## 📦 Instalación

### Opción A — Docker (recomendada) 🐳

Solo necesitas **Docker Desktop**. Levanta la API y PostgreSQL con un comando.

```bash
# 1. Clonar el repositorio
git clone https://github.com/alexisr-dev/caja-backend.git
cd caja-backend

# 2. Crear el archivo de entorno a partir del ejemplo
cp .env.example .env      # en Windows PowerShell: copy .env.example .env

# 3. Construir y levantar los contenedores
docker compose up -d --build
```

La API queda disponible en **http://localhost:8000**. Las migraciones se aplican automáticamente al arrancar.

### Opción B — Instalación manual (venv)

Requiere **Python 3.12+** y una instancia de **PostgreSQL** corriendo localmente.

```bash
# 1. Clonar y entrar al proyecto
git clone https://github.com/alexisr-dev/caja-backend.git
cd caja-backend

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env              # y editar con tus valores

# 5. Migraciones y ejecución
python manage.py migrate
python manage.py runserver
```

---

## ⚙️ Configuración

Todas las variables se definen en un archivo `.env` en la raíz (usa [`.env.example`](.env.example) como plantilla).

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Django (**genera una nueva en producción**) |
| `DEBUG` | `True` en desarrollo, `False` en producción |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma |
| `DJANGO_SETTINGS_MODULE` | Módulo de settings (`core.settings.development` / `.production`) |
| `DB_NAME` · `DB_USER` · `DB_PASSWORD` | Credenciales de PostgreSQL |
| `DB_HOST` · `DB_PORT` | Host y puerto de la BD (ver nota de Docker abajo) |
| `JWT_ACCESS_LIFETIME_MINUTES` | Duración del *access token* (minutos) |
| `JWT_REFRESH_LIFETIME_DAYS` | Duración del *refresh token* (días) |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos para el frontend |
| `MP_PUBLIC_KEY` · `MP_ACCESS_TOKEN` · `MP_WEBHOOK_SECRET` | Credenciales de Mercado Pago |
| `EMAIL_HOST` · `EMAIL_PORT` · `EMAIL_HOST_USER` · `EMAIL_HOST_PASSWORD` | SMTP para 2FA y reset de contraseña |
| `FIREBASE_CREDENTIALS_PATH` | Ruta al `serviceAccountKey.json` de Firebase |
| `GOOGLE_OAUTH_CLIENT_IDS` | Client IDs autorizados para Google Sign-In |
| `IA_SERVICE_URL` · `IA_SERVICE_API_KEY` | URL y API Key del microservicio de IA |
| `IGV_PORCENTAJE` | Porcentaje de IGV aplicado (ej. `0.18`) |

> 💡 **Nota Docker:** dentro de la red de contenedores la base de datos se resuelve por el nombre de servicio `db`. El `docker-compose.yml` ya sobrescribe `DB_HOST=db` automáticamente, así que en tu `.env` puedes dejar `DB_HOST=localhost` para el uso local.

---

## ▶️ Uso

```bash
# Levantar todo (con Docker)
docker compose up -d

# Ver logs del backend en vivo
docker compose logs -f web

# Crear un superusuario (login por email)
docker compose exec web python manage.py createsuperuser

# Apagar los contenedores (los datos de la BD se conservan)
docker compose down
```

Recursos disponibles una vez arriba:

| Recurso | URL |
|---------|-----|
| 🔧 Panel de administración | http://localhost:8000/admin/ |
| 📘 Swagger UI | http://localhost:8000/api/schema/swagger/ |
| 📗 Redoc | http://localhost:8000/api/schema/redoc/ |
| 📄 Esquema OpenAPI | http://localhost:8000/api/schema/ |

**Ejemplo de login (obtener token JWT):**

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ejemplo.com", "password": "tu-password"}'
```

**Usar el token en una petición autenticada:**

```bash
curl http://localhost:8000/api/productos/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## 📁 Estructura del proyecto

```
caja-backend/
├── core/                 # Configuración del proyecto (settings, urls, wsgi/asgi)
│   ├── settings/         # base · development · production
│   ├── exceptions.py     # Manejador de errores personalizado
│   └── pagination.py     # Paginación estándar
├── users/                # Autenticación, JWT, 2FA, Google, roles
├── productos/            # Catálogo, categorías, proveedores, stock, descuentos, favoritos
├── ventas/               # Boletas de venta y carrito persistente
├── pagos/                # Efectivo, Mercado Pago (tarjeta / Yape), webhook
│   └── gateways/         # Integración con la pasarela de pago
├── turnos/               # Apertura y cierre de turnos de caja
├── alertas/              # Alertas de stock y sistema
├── notificaciones/       # Push notifications (FCM) y dispositivos
├── ia_service/           # Cliente del microservicio de reconocimiento por imagen
├── firebase/             # Credenciales FCM (ignoradas por git)
├── manage.py
├── requirements.txt
├── schema.yml            # Esquema OpenAPI exportado
├── Dockerfile
└── docker-compose.yml
```

---

## 🔌 API

Todos los endpoints cuelgan del prefijo `/api/`. La documentación interactiva completa
(con parámetros, cuerpos y respuestas) está en **Swagger UI** y **Redoc**.

| Módulo | Endpoints principales |
|--------|-----------------------|
| **Auth** | `POST /api/auth/registro/` · `POST /api/auth/login/` · `POST /api/auth/login-2fa/` · `POST /api/auth/refresh/` · `POST /api/auth/logout/` · `GET/PUT /api/auth/perfil/` · `POST /api/auth/google/` |
| **Password** | `POST /api/auth/password-reset-request/` · `POST /api/auth/password-reset-confirm/` |
| **Productos** | `GET/POST /api/productos/` · `GET/PUT/DELETE /api/productos/{sku}/` · `GET /api/productos/{sku}/historial-precios/` · `POST /api/productos/{sku}/ajuste-stock/` |
| **Categorías / Proveedores** | `/api/productos/categorias/` · `/api/productos/proveedores/` · `/api/productos/descuentos/` · `/api/productos/favoritos/` |
| **Ventas** | `GET/POST /api/boletas/` · `POST /api/boletas/{id}/cancelar/` · `POST /api/boletas/{id}/anular/` · `GET /api/mis-boletas/` |
| **Carrito** | `GET /api/carrito/` · `POST /api/carrito/items/` · `PUT/DELETE /api/carrito/items/{id}/` |
| **Pagos** | `POST /api/pagos/efectivo/` · `POST /api/pagos/mp-tarjeta/` · `POST /api/pagos/mp-yape/` · `POST /api/pagos/webhook/` |
| **Turnos** | `POST /api/turnos/abrir/` · `POST /api/turnos/cerrar/` · `GET /api/turnos/activo/` · `GET /api/turnos/` |
| **Alertas** | `GET /api/alertas/` · `POST /api/alertas/{id}/marcar-leida/` · `POST /api/alertas/marcar-todas/` |
| **Notificaciones** | `GET /api/notificaciones/` · `POST /api/dispositivos-fcm/` |
| **IA** | `POST /api/escanear/` · `POST /api/registro-visual/` · `GET /api/ia/health/` · `GET /api/logs-escaneos/` |
| **Reportes** | `GET /api/reportes/dashboard/` · `GET /api/reportes/ventas/` · `GET /api/reportes/top-productos/` · `GET /api/reportes/stock-bajo/` |

---

## 🧪 Testing

```bash
# Con Docker
docker compose exec web python manage.py test

# Con entorno local (venv activado)
python manage.py test
```

`<Completar: describir la suite de pruebas y cobertura actual cuando esté disponible.>`

---

## 📈 Roadmap

- [ ] Suite de pruebas automatizadas (unitarias e integración).
- [ ] Pipeline de **CI/CD** (GitHub Actions).
- [ ] Configuración de producción con **Gunicorn + Nginx**.
- [ ] Reporte de cobertura de código.
- [ ] Rate limiting distribuido y caché con Redis.
- [ ] Despliegue en la nube documentado.

---

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Para proponer cambios:

1. Haz un **fork** del repositorio.
2. Crea una rama: `git checkout -b feature/mi-mejora`.
3. Realiza tus cambios y haz **commit**: `git commit -m "Agrega mi mejora"`.
4. Sube la rama: `git push origin feature/mi-mejora`.
5. Abre un **Pull Request** describiendo tu propuesta.

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **GNU Affero General Public License v3.0 (AGPL-3.0)**.

Esto significa que puedes usar, modificar y redistribuir el código, pero **cualquier obra
derivada —incluso si se ofrece como servicio a través de una red— debe publicarse también
bajo AGPL-3.0 y poner su código fuente a disposición**. Se eligió esta licencia por
compatibilidad con las dependencias del sistema de reconocimiento de imágenes (Ultralytics YOLO).

Consulta el archivo [LICENSE](LICENSE) para el texto completo.

---

## 👤 Autor

**Alexis Nehemías Ramírez Merino**

[![GitHub](https://img.shields.io/badge/GitHub-alexisr--dev-181717?style=flat&logo=github)](https://github.com/alexisr-dev)

---

## ⭐ Agradecimientos

- Al ecosistema **Django** y **Django REST Framework** por su excelente documentación.
- A la comunidad *open source* detrás de cada dependencia de este proyecto.
- A **Mercado Pago** y **Firebase** por sus SDKs y entornos de prueba.

<div align="center">

Si este proyecto te resultó útil, ¡considera dejar una ⭐!

</div>
