from django.contrib import admin

from .models import Boleta, DetalleBoleta, CarritoPersistente, ItemCarrito


class DetalleBoletaInline(admin.TabularInline):
    model = DetalleBoleta
    extra = 0
    readonly_fields = ('producto', 'cantidad', 'precio_unitario', 'descuento_aplicado', 'subtotal')

    def has_add_permission(self, request, obj=None):
        return False  # los detalles se crean via API al generar la boleta

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Boleta)
class BoletaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'tipo', 'estado', 'cliente', 'vendedor', 'turno',
                    'total', 'fecha')
    list_filter = ('estado', 'tipo', 'fecha')
    search_fields = ('numero', 'cliente__email', 'vendedor__email')
    autocomplete_fields = ('cliente', 'vendedor', 'turno', 'anulada_por')
    readonly_fields = ('numero', 'fecha', 'subtotal', 'igv', 'total',
                       'anulada_fecha', 'pdf_url')
    inlines = [DetalleBoletaInline]
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Identificacion', {'fields': ('numero', 'tipo', 'fecha', 'estado')}),
        ('Partes', {'fields': ('cliente', 'vendedor', 'turno')}),
        ('Montos', {'fields': ('subtotal', 'igv', 'descuento_global', 'total')}),
        ('Anulacion', {
            'fields': ('anulada_fecha', 'anulada_por', 'anulada_motivo'),
            'classes': ('collapse',),
        }),
        ('Documento', {'fields': ('pdf_url',), 'classes': ('collapse',)}),
    )


class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    autocomplete_fields = ('producto',)


@admin.register(CarritoPersistente)
class CarritoPersistenteAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'cantidad_total', 'actualizado')
    search_fields = ('cliente__email',)
    autocomplete_fields = ('cliente',)
    readonly_fields = ('actualizado',)
    inlines = [ItemCarritoInline]


@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ('carrito', 'producto', 'cantidad', 'agregado')
    autocomplete_fields = ('carrito', 'producto')
    readonly_fields = ('agregado',)
