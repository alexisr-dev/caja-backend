from django.urls import path

from .views import (
    PagoEfectivoView,
    PagoMPTarjetaView,
    PagoMPYapeView,
    WebhookMPView,
    PagoDetailView,
)

urlpatterns = [
    path('pagos/efectivo/',   PagoEfectivoView.as_view(),  name='pago-efectivo'),
    path('pagos/mp-tarjeta/', PagoMPTarjetaView.as_view(), name='pago-mp-tarjeta'),
    path('pagos/mp-yape/',    PagoMPYapeView.as_view(),    name='pago-mp-yape'),
    path('pagos/webhook/',    WebhookMPView.as_view(),     name='pago-webhook-mp'),
    path('pagos/<int:boleta_id>/', PagoDetailView.as_view(), name='pago-detail'),
]
