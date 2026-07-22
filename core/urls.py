from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from .views import (
    DashboardView,
    ReporteVentasView,
    TopProductosView,
    StockBajoView,
    TasaIAView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/auth/', include('users.urls')),
    path('api/', include('productos.urls')),
    path('api/', include('ventas.urls')),
    path('api/', include('pagos.urls')),
    path('api/', include('turnos.urls')),
    path('api/', include('alertas.urls')),
    path('api/', include('notificaciones.urls')),
    path('api/', include('ia_service.urls')),

    path('api/reportes/dashboard/',     DashboardView.as_view(),      name='reporte-dashboard'),
    path('api/reportes/ventas/',        ReporteVentasView.as_view(),  name='reporte-ventas'),
    path('api/reportes/top-productos/', TopProductosView.as_view(),   name='reporte-top-productos'),
    path('api/reportes/stock-bajo/',    StockBajoView.as_view(),      name='reporte-stock-bajo'),
    path('api/reportes/tasa-ia/',       TasaIAView.as_view(),         name='reporte-tasa-ia'),

    path('api/schema/',         SpectacularAPIView.as_view(),                          name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'),     name='swagger-ui'),
    path('api/schema/redoc/',   SpectacularRedocView.as_view(url_name='schema'),       name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
