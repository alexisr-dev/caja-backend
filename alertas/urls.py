from django.urls import path

from .views import AlertaListView, AlertaMarcarLeidaView, AlertaMarcarTodasLeidasView

urlpatterns = [
    path('alertas/',                       AlertaListView.as_view(),           name='alerta-list'),
    path('alertas/marcar-todas/',          AlertaMarcarTodasLeidasView.as_view(), name='alerta-marcar-todas'),
    path('alertas/<int:pk>/marcar-leida/', AlertaMarcarLeidaView.as_view(),    name='alerta-marcar-leida'),
]
