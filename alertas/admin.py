from django.contrib import admin

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo', 'nivel', 'mensaje_truncado', 'producto', 'leida')
    list_filter = ('leida', 'nivel', 'tipo', 'fecha')
    search_fields = ('mensaje', 'producto__sku', 'producto__nombre')
    autocomplete_fields = ('producto',)
    readonly_fields = ('fecha',)
    actions = ['marcar_como_leidas']
    date_hierarchy = 'fecha'

    @admin.display(description='Mensaje')
    def mensaje_truncado(self, obj):
        return obj.mensaje[:80] + ('...' if len(obj.mensaje) > 80 else '')

    @admin.action(description='Marcar como leidas')
    def marcar_como_leidas(self, request, queryset):
        actualizadas = queryset.filter(leida=False).update(leida=True)
        self.message_user(request, f'{actualizadas} alerta(s) marcadas como leidas.')
