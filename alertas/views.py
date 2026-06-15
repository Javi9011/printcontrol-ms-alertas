from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import Alerta, ConfiguracionAlerta, TipoAlerta, NivelAlerta, EstadoAlerta
from .serializers import (
    AlertaSerializer,
    ResolverAlertaSerializer,
    ConfiguracionAlertaSerializer,
    ResumenAlertasSerializer,
)
from .services import ejecutar_motor_alertas


@extend_schema_view(
    list=extend_schema(summary='Listar alertas'),
    retrieve=extend_schema(summary='Detalle de alerta'),
)
class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Alertas generadas por el motor. Solo lectura — se crean automáticamente.
    Las acciones disponibles son: resolver, ignorar y ejecutar el motor.
    """
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tipo', 'nivel', 'estado', 'equipo_id', 'cliente_id']
    search_fields = ['equipo_nombre', 'cliente_nombre', 'mensaje', 'equipo_serial']
    ordering_fields = ['creado_en', 'nivel']
    ordering = ['-creado_en']
    permission_classes = [AllowAny]

    @extend_schema(summary='Solo alertas activas')
    @action(detail=False, methods=['get'], url_path='activas')
    def activas(self, request):
        qs = self.get_queryset().filter(estado=EstadoAlerta.ACTIVA)
        qs = self.filter_queryset(qs)
        serializer = AlertaSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(summary='Resumen para dashboard')
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        hoy = timezone.now().date()
        activas = Alerta.objects.filter(estado=EstadoAlerta.ACTIVA)

        data = {
            'total_activas': activas.count(),
            'criticas': activas.filter(nivel=NivelAlerta.CRITICAL).count(),
            'advertencias': activas.filter(nivel=NivelAlerta.WARNING).count(),
            'toner_bajo': activas.filter(tipo=TipoAlerta.TONER_BAJO).count(),
            'toner_critico': activas.filter(tipo=TipoAlerta.TONER_CRITICO).count(),
            'cuota_excedida': activas.filter(tipo=TipoAlerta.CUOTA_EXCEDIDA).count(),
            'contrato_por_vencer': activas.filter(tipo=TipoAlerta.CONTRATO_POR_VENCER).count(),
            'resueltas_hoy': Alerta.objects.filter(
                estado=EstadoAlerta.RESUELTA,
                resuelta_en__date=hoy
            ).count(),
        }
        return Response(ResumenAlertasSerializer(data).data)

    @extend_schema(
        summary='Resolver una alerta',
        request=ResolverAlertaSerializer,
        responses={200: AlertaSerializer},
    )
    @action(detail=True, methods=['post'], url_path='resolver')
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        serializer = ResolverAlertaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        alerta.estado = EstadoAlerta.RESUELTA
        alerta.resuelta_en = timezone.now()
        alerta.resuelta_por = serializer.validated_data.get('resuelta_por', '')
        alerta.nota_resolucion = serializer.validated_data.get('nota_resolucion', '')
        alerta.save()

        return Response(AlertaSerializer(alerta).data)

    @extend_schema(
        summary='Ignorar una alerta',
        responses={200: AlertaSerializer},
    )
    @action(detail=True, methods=['post'], url_path='ignorar')
    def ignorar(self, request, pk=None):
        alerta = self.get_object()
        alerta.estado = EstadoAlerta.IGNORADA
        alerta.save(update_fields=['estado', 'actualizado_en'])
        return Response(AlertaSerializer(alerta).data)

    @extend_schema(
        summary='Ejecutar motor de alertas manualmente',
        responses={200: {'type': 'object', 'properties': {
            'status': {'type': 'string'},
            'nuevas_alertas': {'type': 'integer'},
        }}},
    )
    @action(detail=False, methods=['post'], url_path='ejecutar-motor')
    def ejecutar_motor(self, request):
        """
        Dispara el motor de alertas de forma inmediata.
        En producción esto lo hace Celery Beat cada hora automáticamente.
        """
        total = ejecutar_motor_alertas()
        return Response({'status': 'ok', 'nuevas_alertas': total})


@extend_schema_view(
    list=extend_schema(summary='Listar configuraciones'),
    retrieve=extend_schema(summary='Detalle de configuración'),
    create=extend_schema(summary='Crear configuración'),
    update=extend_schema(summary='Actualizar configuración'),
    partial_update=extend_schema(summary='Actualizar parcialmente'),
    destroy=extend_schema(summary='Eliminar configuración'),
)
class ConfiguracionAlertaViewSet(viewsets.ModelViewSet):
    """
    Umbrales configurables del motor de alertas.
    Claves soportadas:
    - toner_warning_pct (default 15)
    - toner_critical_pct (default 5)
    - cuota_excedida_pct (default 110)
    - contrato_vencer_dias (default 30)
    """
    queryset = ConfiguracionAlerta.objects.all()
    serializer_class = ConfiguracionAlertaSerializer
    permission_classes = [AllowAny]
