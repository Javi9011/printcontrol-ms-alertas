from django.contrib import admin
from django.utils.html import format_html
from .models import Alerta, ConfiguracionAlerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = [
        'nivel_badge', 'tipo', 'equipo_nombre', 'cliente_nombre',
        'estado', 'creado_en', 'resuelta_en'
    ]
    list_filter = ['nivel', 'tipo', 'estado']
    search_fields = ['equipo_nombre', 'cliente_nombre', 'mensaje', 'equipo_serial']
    readonly_fields = ['creado_en', 'actualizado_en']

    def nivel_badge(self, obj):
        colors = {
            'CRITICAL': '#E24B4A',
            'WARNING': '#EF9F27',
            'INFO': '#185FA5',
        }
        color = colors.get(obj.nivel, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:bold">{}</span>',
            color, obj.nivel
        )
    nivel_badge.short_description = 'Nivel'


@admin.register(ConfiguracionAlerta)
class ConfiguracionAlertaAdmin(admin.ModelAdmin):
    list_display = ['clave', 'valor', 'descripcion', 'actualizado_en']
    search_fields = ['clave']
