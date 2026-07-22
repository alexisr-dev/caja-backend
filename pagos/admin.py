from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('boleta', 'metodo', 'submetodo', 'monto', 'estado',
                    'referencia_mp', 'fecha')
    list_filter = ('metodo', 'submetodo', 'estado', 'fecha')
    search_fields = ('boleta__numero', 'referencia_mp')
    autocomplete_fields = ('boleta',)
    readonly_fields = ('vuelto', 'respuesta_gateway', 'fecha', 'actualizado')
    fieldsets = (
        ('Boleta', {'fields': ('boleta', 'monto')}),
        ('Metodo', {'fields': ('metodo', 'submetodo')}),
        ('Efectivo', {
            'fields': ('monto_recibido', 'vuelto'),
            'classes': ('collapse',),
        }),
        ('Mercado Pago', {
            'fields': ('referencia_mp', 'respuesta_gateway'),
            'classes': ('collapse',),
        }),
        ('Estado', {'fields': ('estado', 'fecha', 'actualizado')}),
    )
