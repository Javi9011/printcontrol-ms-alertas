from rest_framework import serializers
from .models import Alerta, ConfiguracionAlerta


class AlertaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    nivel_display = serializers.CharField(source='get_nivel_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Alerta
        fields = [
            'id', 'tipo', 'tipo_display',
            'nivel', 'nivel_display',
            'estado', 'estado_display',
            'equipo_id', 'equipo_nombre', 'equipo_serial',
            'cliente_id', 'cliente_nombre',
            'contrato_id', 'contrato_numero',
            'mensaje', 'datos_extra',
            'resuelta_en', 'resuelta_por', 'nota_resolucion',
            'creado_en', 'actualizado_en',
        ]
        read_only_fields = ['creado_en', 'actualizado_en']


class ResolverAlertaSerializer(serializers.Serializer):
    nota_resolucion = serializers.CharField(required=False, allow_blank=True, default='')
    resuelta_por = serializers.CharField(required=False, allow_blank=True, default='')


class ConfiguracionAlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionAlerta
        fields = ['id', 'clave', 'valor', 'descripcion', 'actualizado_en']
        read_only_fields = ['actualizado_en']


class ResumenAlertasSerializer(serializers.Serializer):
    total_activas = serializers.IntegerField()
    criticas = serializers.IntegerField()
    advertencias = serializers.IntegerField()
    toner_bajo = serializers.IntegerField()
    toner_critico = serializers.IntegerField()
    cuota_excedida = serializers.IntegerField()
    contrato_por_vencer = serializers.IntegerField()
    resueltas_hoy = serializers.IntegerField()
