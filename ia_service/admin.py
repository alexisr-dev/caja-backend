from django.contrib import admin

from .models import LogEscaneoIA


@admin.register(LogEscaneoIA)
class LogEscaneoIAAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'modo', 'resultado', 'producto_detectado',
                    'confianza', 'latencia_ms', 'usuario')
    list_filter = ('resultado', 'modo', 'fecha')
    search_fields = ('usuario__email', 'producto_detectado__sku')
    autocomplete_fields = ('usuario', 'producto_detectado')
    readonly_fields = ('fecha',)
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False  # solo se crea por el endpoint de escaneo
