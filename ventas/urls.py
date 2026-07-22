from django.urls import path

from .views import (
    BoletaListCreateView,
    BoletaDetailView,
    BoletaCancelarView,
    BoletaAnularView,
    MisBoletasView,
    CarritoView,
    ItemCarritoCreateView,
    ItemCarritoUpdateView,
    ItemCarritoDeleteView,
)

urlpatterns = [
    path('boletas/',               BoletaListCreateView.as_view(), name='boleta-list'),
    path('boletas/<int:pk>/',      BoletaDetailView.as_view(),     name='boleta-detail'),
    path('boletas/<int:pk>/cancelar/', BoletaCancelarView.as_view(), name='boleta-cancelar'),
    path('boletas/<int:pk>/anular/', BoletaAnularView.as_view(),   name='boleta-anular'),
    path('mis-boletas/',           MisBoletasView.as_view(),       name='mis-boletas'),

    path('carrito/',               CarritoView.as_view(),          name='carrito'),
    path('carrito/items/',         ItemCarritoCreateView.as_view(), name='carrito-item-create'),
    path('carrito/items/<int:pk>/', ItemCarritoUpdateView.as_view(), name='carrito-item-update'),
    path('carrito/items/<int:pk>/delete/', ItemCarritoDeleteView.as_view(), name='carrito-item-delete'),
]
