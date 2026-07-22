from django.urls import path

from .views import (
    TurnoAbrirView,
    TurnoCerrarView,
    TurnoActivoView,
    TurnoListView,
    TurnoDetailView,
)

urlpatterns = [
    path('turnos/abrir/',    TurnoAbrirView.as_view(),   name='turno-abrir'),
    path('turnos/cerrar/',   TurnoCerrarView.as_view(),  name='turno-cerrar'),
    path('turnos/activo/',   TurnoActivoView.as_view(),  name='turno-activo'),
    path('turnos/',          TurnoListView.as_view(),    name='turno-list'),
    path('turnos/<int:pk>/', TurnoDetailView.as_view(),  name='turno-detail'),
]
