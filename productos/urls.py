from django.urls import path

from .views import (
    CategoriaListCreateView,
    CategoriaDetailView,
    ProveedorListCreateView,
    ProveedorDetailView,
    ProductoListCreateView,
    ProductoDetailView,
    ProductoHistorialPreciosView,
    ProductoAjusteStockView,
    FotoProductoCreateView,
    FotoProductoDeleteView,
    DescuentoListCreateView,
    DescuentoDetailView,
    FavoritoListCreateView,
    FavoritoDeleteView,
)

urlpatterns = [

    path('productos/categorias/',           CategoriaListCreateView.as_view(), name='categoria-list'),
    path('productos/categorias/<int:pk>/',  CategoriaDetailView.as_view(),     name='categoria-detail'),

    path('productos/proveedores/',          ProveedorListCreateView.as_view(), name='proveedor-list'),
    path('productos/proveedores/<int:pk>/', ProveedorDetailView.as_view(),     name='proveedor-detail'),

    path('productos/fotos/<int:pk>/',       FotoProductoDeleteView.as_view(),  name='foto-delete'),

    path('productos/descuentos/',           DescuentoListCreateView.as_view(), name='descuento-list'),
    path('productos/descuentos/<int:pk>/',  DescuentoDetailView.as_view(),     name='descuento-detail'),

    path('productos/favoritos/',            FavoritoListCreateView.as_view(),  name='favorito-list'),
    path('productos/favoritos/<int:pk>/',   FavoritoDeleteView.as_view(),      name='favorito-delete'),

    path('productos/',                               ProductoListCreateView.as_view(),        name='producto-list'),
    path('productos/<str:sku>/',                     ProductoDetailView.as_view(),            name='producto-detail'),
    path('productos/<str:sku>/historial-precios/',   ProductoHistorialPreciosView.as_view(),  name='producto-historial-precios'),
    path('productos/<str:sku>/ajuste-stock/',        ProductoAjusteStockView.as_view(),       name='producto-ajuste-stock'),
    path('productos/<str:sku>/fotos/',               FotoProductoCreateView.as_view(),        name='producto-foto-create'),
]
