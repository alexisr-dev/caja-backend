from django.urls import path

from .views import (
    EscanearView,
    RegistroVisualView,
    LogEscaneoListView,
    IAHealthView,
    IACatalogoStatsView,
)

urlpatterns = [
    path('escanear/',          EscanearView.as_view(),        name='ia-escanear'),
    path('registro-visual/',   RegistroVisualView.as_view(),  name='ia-registro-visual'),
    path('logs-escaneos/',     LogEscaneoListView.as_view(),  name='ia-logs-escaneos'),
    path('ia/health/',         IAHealthView.as_view(),        name='ia-health'),
    path('ia/catalogo/stats/', IACatalogoStatsView.as_view(), name='ia-catalogo-stats'),
]
