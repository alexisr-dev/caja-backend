from django.urls import path

from .views import (
    NotificacionListView,
    NotificacionMarcarLeidaView,
    NotificacionMarcarTodasView,
    DispositivoFCMCreateView,
    DispositivoFCMDeleteView,
)

urlpatterns = [
    path('notificaciones/',                      NotificacionListView.as_view(),       name='notificacion-list'),
    path('notificaciones/marcar-todas/',         NotificacionMarcarTodasView.as_view(), name='notificacion-marcar-todas'),
    path('notificaciones/<int:pk>/marcar-leida/', NotificacionMarcarLeidaView.as_view(), name='notificacion-marcar-leida'),
    path('dispositivos-fcm/',         DispositivoFCMCreateView.as_view(), name='dispositivo-fcm-create'),
    path('dispositivos-fcm/<int:pk>/', DispositivoFCMDeleteView.as_view(), name='dispositivo-fcm-delete'),
]
