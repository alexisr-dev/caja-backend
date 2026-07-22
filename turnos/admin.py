from django.contrib import admin

from .models import TurnoCaja


@admin.register(TurnoCaja)
class TurnoCajaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'vendedor', 'estado', 'apertura_fecha',
        'monto_inicial', 'cierre_fecha', 'monto_contado_cierre',
        'diagnostico_display',
    )
    list_filter = ('estado', 'apertura_fecha')
    search_fields = ('vendedor__email',)
    autocomplete_fields = ('vendedor',)
    readonly_fields = (
        'apertura_fecha',
        'total_ventas_efectivo_display',
        'esperado_en_caja_display',
        'diferencia_display',
        'diagnostico_display',
    )
    fieldsets = (
        ('Apertura', {'fields': ('vendedor', 'apertura_fecha', 'monto_inicial')}),
        ('Cierre', {'fields': ('estado', 'cierre_fecha', 'monto_contado_cierre', 'observaciones')}),
        ('Calculos', {'fields': (
            'total_ventas_efectivo_display',
            'esperado_en_caja_display',
            'diferencia_display',
            'diagnostico_display',
        )}),
    )

    @admin.display(description='Ventas efectivo')
    def total_ventas_efectivo_display(self, obj):
        return f'S/ {obj.total_ventas_efectivo}'

    @admin.display(description='Esperado en caja')
    def esperado_en_caja_display(self, obj):
        return f'S/ {obj.esperado_en_caja}'

    @admin.display(description='Diferencia')
    def diferencia_display(self, obj):
        diff = obj.diferencia
        return f'S/ {diff}' if diff is not None else '-'

    @admin.display(description='Diagnostico')
    def diagnostico_display(self, obj):
        return obj.diagnostico
