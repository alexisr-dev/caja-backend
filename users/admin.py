from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, TokenRecuperacionPassword, CodigoVerificacion2FA

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'rol', 'first_name', 'last_name', 'dni', 'es_demo', 'is_active', 'fecha_registro')
    list_filter = ('rol', 'es_demo', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'dni')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Datos personales', {'fields': ('first_name', 'last_name', 'telefono', 'direccion', 'dni')}),
        ('Rol y permisos', {'fields': ('rol', 'es_demo', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Google Sign-In', {'fields': ('google_id', 'avatar_url'), 'classes': ('collapse',)}),
        ('Fechas', {'fields': ('last_login', 'date_joined', 'fecha_registro')}),
    )
    readonly_fields = ('fecha_registro', 'date_joined', 'last_login')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'rol', 'es_demo'),
        }),
    )

@admin.register(TokenRecuperacionPassword)
class TokenRecuperacionPasswordAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'codigo', 'usado', 'creado', 'expira')
    list_filter = ('usado',)
    search_fields = ('usuario__email',)
    readonly_fields = ('codigo', 'creado', 'expira')

@admin.register(CodigoVerificacion2FA)
class CodigoVerificacion2FAAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'codigo', 'usado', 'creado', 'expira')
    list_filter = ('usado',)
    search_fields = ('usuario__email',)
    readonly_fields = ('codigo', 'creado', 'expira')
