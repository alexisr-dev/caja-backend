from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdmin, IsAdminOrVendedor

@extend_schema(tags=['reportes'])
class DashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from ventas.models import Boleta
        from alertas.models import Alerta
        from ia_service.models import LogEscaneoIA

        ahora = timezone.now()
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        semana_inicio = hoy_inicio - timedelta(days=ahora.weekday())
        mes_inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def resumen_boletas(qs):
            agg = qs.filter(estado='PAGADA').aggregate(
                cantidad=Count('id'),
                total=Sum('total'),
            )
            return {
                'cantidad': agg['cantidad'] or 0,
                'total': str(agg['total'] or Decimal('0.00')),
            }

        boletas = Boleta.objects.all()

        alertas_qs = Alerta.objects.filter(leida=False).values('nivel').annotate(n=Count('id'))
        alertas_por_nivel = {row['nivel']: row['n'] for row in alertas_qs}

        hace_24h = ahora - timedelta(hours=24)
        logs_24h = LogEscaneoIA.objects.filter(fecha__gte=hace_24h)
        total_logs = logs_24h.count()
        logs_ok = logs_24h.filter(resultado='OK').count()
        tasa_ia = round(logs_ok / total_logs * 100, 1) if total_logs else None

        return Response({
            'ventas_hoy': resumen_boletas(boletas.filter(fecha__gte=hoy_inicio)),
            'ventas_semana': resumen_boletas(boletas.filter(fecha__gte=semana_inicio)),
            'ventas_mes': resumen_boletas(boletas.filter(fecha__gte=mes_inicio)),
            'alertas_no_leidas': {
                'total': sum(alertas_por_nivel.values()),
                'critico': alertas_por_nivel.get('CRITICO', 0),
                'advertencia': alertas_por_nivel.get('ADVERTENCIA', 0),
                'info': alertas_por_nivel.get('INFO', 0),
            },
            'tasa_reconocimiento_ia_24h': tasa_ia,
            'escaneos_24h': total_logs,
        })

@extend_schema(tags=['reportes'])
class ReporteVentasView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from ventas.models import Boleta
        from django.db.models.functions import TruncDate

        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')

        qs = Boleta.objects.filter(estado='PAGADA')
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)

        totales = qs.aggregate(
            boletas=Count('id'),
            total_ventas=Sum('total'),
            ticket_promedio=Avg('total'),
        )

        por_dia = (
            qs.annotate(dia=TruncDate('fecha'))
            .values('dia')
            .annotate(boletas=Count('id'), total=Sum('total'))
            .order_by('dia')
        )

        return Response({
            'resumen': {
                'boletas': totales['boletas'] or 0,
                'total_ventas': str(totales['total_ventas'] or Decimal('0.00')),
                'ticket_promedio': str(
                    (totales['ticket_promedio'] or Decimal('0.00')).quantize(Decimal('0.01'))
                ),
            },
            'por_dia': [
                {
                    'fecha': row['dia'],
                    'boletas': row['boletas'],
                    'total': str(row['total'] or Decimal('0.00')),
                }
                for row in por_dia
            ],
        })

@extend_schema(tags=['reportes'])
class TopProductosView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def get(self, request):
        from productos.models import Producto
        from productos.serializers import ProductoListSerializer

        limit = min(int(request.query_params.get('limit', 10)), 50)
        productos = Producto.objects.filter(activo=True).order_by('-contador_ventas')[:limit]
        return Response(ProductoListSerializer(productos, many=True).data)

@extend_schema(tags=['reportes'])
class StockBajoView(APIView):
    permission_classes = [IsAdminOrVendedor]

    def get(self, request):
        from django.db.models import F
        from productos.models import Producto
        from productos.serializers import ProductoListSerializer

        agotados = Producto.objects.filter(activo=True, stock=0)
        bajos = Producto.objects.filter(activo=True, stock__gt=0, stock__lte=F('stock_minimo'))

        return Response({
            'agotados': {
                'cantidad': agotados.count(),
                'productos': ProductoListSerializer(agotados, many=True).data,
            },
            'stock_bajo': {
                'cantidad': bajos.count(),
                'productos': ProductoListSerializer(bajos, many=True).data,
            },
        })

@extend_schema(tags=['reportes'])
class TasaIAView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from ia_service.models import LogEscaneoIA

        horas = min(int(request.query_params.get('horas', 24)), 720)
        desde = timezone.now() - timedelta(hours=horas)

        qs = LogEscaneoIA.objects.filter(fecha__gte=desde)
        total = qs.count()

        por_resultado = {
            row['resultado']: row['n']
            for row in qs.values('resultado').annotate(n=Count('id'))
        }

        ok = por_resultado.get('OK', 0)
        tasa = round(ok / total * 100, 1) if total else None

        latencia_avg = qs.filter(resultado='OK').aggregate(avg=Avg('latencia_ms'))['avg']

        return Response({
            'periodo_horas': horas,
            'total_escaneos': total,
            'tasa_reconocimiento': tasa,
            'por_resultado': por_resultado,
            'latencia_promedio_ms': round(latencia_avg) if latencia_avg else None,
        })
