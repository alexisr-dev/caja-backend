from django.apps import AppConfig

class ProductosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'productos'
    verbose_name = 'Productos e Inventario'

    def ready(self):
        from . import signals
