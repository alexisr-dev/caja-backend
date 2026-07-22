from django.contrib import admin

from .models import DispositivoFCM, Notificacion


@admin.register(DispositivoFCM)
class DispositivoFCMAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'plataforma', 'activo', 'registrado', 'ultima_actividad')
    list_filter = ('activo', 'plataforma')
    search_fields = ('usuario__email', 'token_fcm')
    autocomplete_fields = ('usuario',)
    readonly_fields = ('token_fcm', 'registrado', 'ultima_actividad')


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('fecha_envio', 'usuario', 'tipo', 'titulo', 'leida')
    list_filter = ('leida', 'tipo', 'fecha_envio')
    search_fields = ('usuario__email', 'titulo', 'cuerpo')
    autocomplete_fields = ('usuario',)
    readonly_fields = ('fecha_envio',)
    date_hierarchy = 'fecha_envio'
