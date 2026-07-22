from django.contrib import admin

from .models import (
    Categoria,
    Proveedor,
    Producto,
    FotoProducto,
    HistorialPrecio,
    Descuento,
    Favorito,
    MovimientoStock,
)

class FotoProductoInline(admin.TabularInline):
    model = FotoProducto
    extra = 1
    fields = ('imagen', 'orden')

class VarianteInline(admin.TabularInline):
    model = Producto
    extra = 0
    fk_name = 'padre'
    fields = ('sku', 'nombre', 'precio', 'stock')
    show_change_link = True

class DescuentoInline(admin.TabularInline):
    model = Descuento
    extra = 0
    fields = ('tipo', 'valor', 'lleva_n', 'paga_m', 'fecha_inicio', 'fecha_fin', 'activo')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('ruc', 'razon_social', 'telefono', 'email', 'activo')
    list_filter = ('activo',)
    search_fields = ('ruc', 'razon_social', 'persona_contacto')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('sku', 'nombre', 'categoria', 'precio', 'stock', 'stock_minimo',
                    'fecha_vencimiento', 'activo')
    list_filter = ('activo', 'categoria', 'proveedor')
    search_fields = ('sku', 'nombre')
    autocomplete_fields = ('categoria', 'proveedor', 'padre')
    readonly_fields = ('contador_ventas', 'creado', 'actualizado')
    inlines = [FotoProductoInline, VarianteInline, DescuentoInline]
    fieldsets = (
        (None, {'fields': ('sku', 'nombre', 'descripcion')}),
        ('Precios y stock', {'fields': ('precio', 'stock', 'stock_minimo', 'fecha_vencimiento')}),
        ('Clasificacion', {'fields': ('categoria', 'proveedor', 'padre')}),
        ('Imagen y estado', {'fields': ('imagen_principal', 'activo')}),
        ('Metricas', {'fields': ('contador_ventas', 'creado', 'actualizado'), 'classes': ('collapse',)}),
    )

@admin.register(HistorialPrecio)
class HistorialPrecioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'precio_anterior', 'precio_nuevo', 'usuario', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('producto__sku', 'producto__nombre')
    readonly_fields = ('producto', 'precio_anterior', 'precio_nuevo', 'usuario', 'fecha', 'motivo')

    def has_add_permission(self, request):
        return False

@admin.register(Descuento)
class DescuentoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'valor', 'lleva_n', 'paga_m',
                    'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('producto__sku', 'producto__nombre')
    autocomplete_fields = ('producto',)

@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'producto', 'creado')
    search_fields = ('cliente__email', 'producto__sku')
    autocomplete_fields = ('cliente', 'producto')

@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'cantidad', 'usuario', 'fecha', 'boleta')
    list_filter = ('tipo', 'fecha')
    search_fields = ('producto__sku', 'motivo')
    autocomplete_fields = ('producto', 'usuario', 'boleta')
    readonly_fields = ('fecha',)
