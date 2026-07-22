from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Descuento, Producto, HistorialPrecio

@receiver(pre_save, sender=Producto)
def capturar_precio_anterior(sender, instance: Producto, **kwargs):
    if not instance.pk:
        return
    try:
        previo = Producto.objects.only('precio').get(pk=instance.pk)
    except Producto.DoesNotExist:
        return

    if previo.precio != instance.precio:
        instance._precio_anterior = previo.precio

@receiver(post_save, sender=Producto)
def registrar_historial_precio(sender, instance: Producto, created: bool, **kwargs):
    if created:
        return
    precio_anterior = getattr(instance, '_precio_anterior', None)
    if precio_anterior is None:
        return

    HistorialPrecio.objects.create(
        producto=instance,
        precio_anterior=precio_anterior,
        precio_nuevo=instance.precio,
    )
    del instance._precio_anterior

@receiver(pre_save, sender=Descuento)
def capturar_activo_anterior(sender, instance: Descuento, **kwargs):
    if not instance.pk:
        return
    try:
        previo = Descuento.objects.only('activo').get(pk=instance.pk)
        instance._activo_anterior = previo.activo
    except Descuento.DoesNotExist:
        pass

@receiver(post_save, sender=Descuento)
def notificar_nuevo_descuento(sender, instance: Descuento, created: bool, **kwargs):
    activo_anterior = getattr(instance, '_activo_anterior', None)
    es_nueva_activacion = (
        (created and instance.activo)
        or (not created and activo_anterior is False and instance.activo)
    )
    if not es_nueva_activacion:
        return

    from django.contrib.auth import get_user_model
    from notificaciones.utils import enviar_notificacion_push

    User = get_user_model()
    staff = User.objects.filter(is_active=True, rol__in=['VENDEDOR', 'CLIENTE'])

    nombre = instance.producto.nombre
    if instance.tipo == 'PORCENTAJE':
        titulo = f'¡Oferta en {nombre}!'
        cuerpo = f'{instance.valor}% de descuento'
    elif instance.tipo == 'MONTO_FIJO':
        titulo = f'¡Oferta en {nombre}!'
        cuerpo = f'S/ {instance.valor} de descuento'
    else:
        titulo = f'¡Promoción en {nombre}!'
        cuerpo = f'Lleva {instance.lleva_n}, paga {instance.paga_m}'
    data = {
        'tipo': 'OFERTA',
        'descuento_id': str(instance.pk),
        'producto_id': str(instance.producto_id),
    }

    for usuario in staff:
        enviar_notificacion_push(usuario, titulo=titulo, cuerpo=cuerpo, data=data)
