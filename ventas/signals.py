from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Boleta

@receiver(pre_save, sender=Boleta)
def capturar_estado_anterior(sender, instance: Boleta, **kwargs):
    if not instance.pk:
        instance._estado_anterior = None
        return
    try:
        previo = Boleta.objects.only('estado').get(pk=instance.pk)
        instance._estado_anterior = previo.estado
    except Boleta.DoesNotExist:
        instance._estado_anterior = None

@receiver(post_save, sender=Boleta)
def manejar_cambio_estado(sender, instance: Boleta, created: bool, **kwargs):
    estado_anterior = getattr(instance, '_estado_anterior', None)
    estado_actual = instance.estado

    if estado_actual == estado_anterior:
        return

    if estado_actual == Boleta.Estado.PAGADA:
        _procesar_pago(instance)
    elif estado_actual == Boleta.Estado.ANULADA and estado_anterior == Boleta.Estado.PAGADA:
        _procesar_anulacion(instance)

def _procesar_pago(boleta: Boleta) -> None:
    from productos.models import MovimientoStock
    from alertas.models import Alerta
    from notificaciones.utils import enviar_notificacion_push

    actor = boleta.vendedor or boleta.cliente

    with transaction.atomic():
        for det in boleta.detalles.select_related('producto').all():
            producto = det.producto

            producto.stock = max(0, producto.stock - det.cantidad)
            producto.contador_ventas += det.cantidad
            producto.save(update_fields=['stock', 'contador_ventas', 'actualizado'])

            MovimientoStock.objects.create(
                producto=producto,
                tipo=MovimientoStock.Tipo.SALIDA,
                cantidad=det.cantidad,
                usuario=actor,
                motivo=f'Venta {boleta.numero}',
                boleta=boleta,
            )

            if producto.stock == 0:
                Alerta.objects.create(
                    tipo=Alerta.Tipo.STOCK_AGOTADO,
                    nivel=Alerta.Nivel.CRITICO,
                    mensaje=f'{producto.nombre} se agoto',
                    producto=producto,
                )
            elif producto.stock <= producto.stock_minimo:
                Alerta.objects.create(
                    tipo=Alerta.Tipo.STOCK_BAJO,
                    nivel=Alerta.Nivel.ADVERTENCIA,
                    mensaje=f'{producto.nombre} stock bajo ({producto.stock})',
                    producto=producto,
                )

    if boleta.cliente:
        try:
            enviar_notificacion_push(
                boleta.cliente,
                titulo='Compra exitosa',
                cuerpo=f'Boleta {boleta.numero} - Total S/ {boleta.total}',
                data={'boleta_id': boleta.pk, 'tipo': 'COMPRA_EXITOSA'},
            )
        except Exception:
            pass

def _procesar_anulacion(boleta: Boleta) -> None:
    from productos.models import MovimientoStock

    if boleta.anulada_fecha is None:
        Boleta.objects.filter(pk=boleta.pk).update(
            anulada_fecha=timezone.now(),
        )

    with transaction.atomic():
        for det in boleta.detalles.select_related('producto').all():
            producto = det.producto

            producto.stock += det.cantidad
            producto.contador_ventas = max(0, producto.contador_ventas - det.cantidad)
            producto.save(update_fields=['stock', 'contador_ventas', 'actualizado'])

            MovimientoStock.objects.create(
                producto=producto,
                tipo=MovimientoStock.Tipo.ANULACION,
                cantidad=det.cantidad,
                usuario=boleta.anulada_por,
                motivo=f'Anulacion {boleta.numero}: {boleta.anulada_motivo}',
                boleta=boleta,
            )
