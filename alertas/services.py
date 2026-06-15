"""
Motor de alertas — consulta ms-equipos y ms-clientes
y genera/actualiza alertas en la base de datos local.
"""
import logging
from datetime import date, timedelta

import httpx
from django.conf import settings
from django.utils import timezone

from .models import Alerta, ConfiguracionAlerta, TipoAlerta, NivelAlerta, EstadoAlerta

logger = logging.getLogger(__name__)


def _get(url: str) -> list | dict | None:
    """HTTP GET con timeout. Retorna None si falla."""
    try:
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.error('Error consultando %s: %s', url, exc)
        return None


def _config(clave: str, default) -> float:
    val = ConfiguracionAlerta.get(clave)
    try:
        return float(val) if val is not None else default
    except ValueError:
        return default


def _upsert_alerta(tipo, nivel, equipo_id=None, equipo_nombre='', equipo_serial='',
                   cliente_id=None, cliente_nombre='', contrato_id=None,
                   contrato_numero='', mensaje='', datos_extra=None):
    """
    Crea la alerta si no existe activa, o la actualiza si ya existe.
    Evita duplicados para el mismo equipo+tipo.
    """
    filtros = {'tipo': tipo, 'estado': EstadoAlerta.ACTIVA}
    if equipo_id:
        filtros['equipo_id'] = equipo_id
    if contrato_id and not equipo_id:
        filtros['contrato_id'] = contrato_id

    alerta, creada = Alerta.objects.update_or_create(
        **filtros,
        defaults={
            'nivel': nivel,
            'equipo_nombre': equipo_nombre,
            'equipo_serial': equipo_serial,
            'cliente_id': cliente_id,
            'cliente_nombre': cliente_nombre,
            'contrato_id': contrato_id,
            'contrato_numero': contrato_numero,
            'mensaje': mensaje,
            'datos_extra': datos_extra or {},
        }
    )
    return alerta, creada


def resolver_alerta(tipo, equipo_id=None, contrato_id=None):
    """Marca como resuelta una alerta activa cuando la condición ya no aplica."""
    filtros = {'tipo': tipo, 'estado': EstadoAlerta.ACTIVA}
    if equipo_id:
        filtros['equipo_id'] = equipo_id
    if contrato_id and not equipo_id:
        filtros['contrato_id'] = contrato_id

    Alerta.objects.filter(**filtros).update(
        estado=EstadoAlerta.RESUELTA,
        resuelta_en=timezone.now(),
        nota_resolucion='Resuelta automáticamente por el motor de alertas',
    )


# ─────────────────────────────────────────────────────────────────────────────
# ALERTAS DE TÓNER
# ─────────────────────────────────────────────────────────────────────────────

def verificar_alertas_toner():
    """
    Consulta ms-equipos y genera alertas de tóner bajo/crítico.
    """
    warning_pct = _config('toner_warning_pct', 15)
    critical_pct = _config('toner_critical_pct', 5)

    url = f'{settings.MS_EQUIPOS_URL}/api/v1/equipos/?page_size=1000'
    data = _get(url)
    if not data:
        return 0

    equipos = data.get('results', data) if isinstance(data, dict) else data
    generadas = 0

    for eq in equipos:
        equipo_id = eq.get('id')
        equipo_nombre = eq.get('nombre', '')
        equipo_serial = eq.get('numero_serie', '')
        cliente_id = eq.get('cliente_id')

        for toner in eq.get('toners', []):
            canal = toner.get('canal')
            canal_display = toner.get('canal_display', canal)
            pct = float(toner.get('porcentaje_restante', 100))

            if pct <= critical_pct:
                tipo = TipoAlerta.TONER_CRITICO
                nivel = NivelAlerta.CRITICAL
                mensaje = (
                    f'Tóner {canal_display} del equipo {equipo_nombre} '
                    f'({equipo_serial}) al {pct}% — requiere cambio inmediato.'
                )
            elif pct <= warning_pct:
                tipo = TipoAlerta.TONER_BAJO
                nivel = NivelAlerta.WARNING
                mensaje = (
                    f'Tóner {canal_display} del equipo {equipo_nombre} '
                    f'({equipo_serial}) al {pct}% — programar cambio pronto.'
                )
            else:
                # Tóner OK — resolver alertas previas si las había
                resolver_alerta(TipoAlerta.TONER_CRITICO, equipo_id=f'{equipo_id}_{canal}')
                resolver_alerta(TipoAlerta.TONER_BAJO, equipo_id=f'{equipo_id}_{canal}')
                continue

            _, creada = _upsert_alerta(
                tipo=tipo,
                nivel=nivel,
                equipo_id=equipo_id,
                equipo_nombre=equipo_nombre,
                equipo_serial=equipo_serial,
                cliente_id=cliente_id,
                mensaje=mensaje,
                datos_extra={
                    'canal': canal,
                    'canal_display': canal_display,
                    'porcentaje_restante': pct,
                    'paginas_restantes': toner.get('paginas_restantes'),
                    'capacidad_paginas': toner.get('capacidad_paginas'),
                }
            )
            if creada:
                generadas += 1

    logger.info('Alertas tóner procesadas. Nuevas: %d', generadas)
    return generadas


# ─────────────────────────────────────────────────────────────────────────────
# ALERTAS DE CUOTA EXCEDIDA
# ─────────────────────────────────────────────────────────────────────────────

def verificar_alertas_cuota():
    """
    Consulta ms-equipos y genera alertas cuando los ciclos del mes
    superan el umbral configurado (default 110% de la cuota mensual).
    """
    cuota_pct = _config('cuota_excedida_pct', 110)

    url = f'{settings.MS_EQUIPOS_URL}/api/v1/equipos/?page_size=1000'
    data = _get(url)
    if not data:
        return 0

    equipos = data.get('results', data) if isinstance(data, dict) else data
    generadas = 0

    for eq in equipos:
        equipo_id = eq.get('id')
        ciclos = eq.get('ciclos_ultimo_mes')
        cuota = eq.get('cuota_mensual', 0)

        if ciclos is None or cuota == 0:
            continue

        ratio = (ciclos / cuota) * 100

        if ratio >= cuota_pct:
            mensaje = (
                f'Equipo {eq.get("nombre")} ({eq.get("numero_serie")}) '
                f'ha consumido {ciclos:,} ciclos este mes '
                f'({ratio:.1f}% de la cuota de {cuota:,}).'
            )
            _, creada = _upsert_alerta(
                tipo=TipoAlerta.CUOTA_EXCEDIDA,
                nivel=NivelAlerta.WARNING,
                equipo_id=equipo_id,
                equipo_nombre=eq.get('nombre', ''),
                equipo_serial=eq.get('numero_serie', ''),
                cliente_id=eq.get('cliente_id'),
                mensaje=mensaje,
                datos_extra={
                    'ciclos_mes': ciclos,
                    'cuota_mensual': cuota,
                    'porcentaje_uso': round(ratio, 1),
                }
            )
            if creada:
                generadas += 1
        else:
            resolver_alerta(TipoAlerta.CUOTA_EXCEDIDA, equipo_id=equipo_id)

    logger.info('Alertas cuota procesadas. Nuevas: %d', generadas)
    return generadas


# ─────────────────────────────────────────────────────────────────────────────
# ALERTAS DE CONTRATOS
# ─────────────────────────────────────────────────────────────────────────────

def verificar_alertas_contratos():
    """
    Consulta ms-clientes y genera alertas para contratos
    próximos a vencer o ya vencidos.
    """
    dias_aviso = int(_config('contrato_vencer_dias', 30))
    hoy = date.today()
    generadas = 0

    # Contratos por vencer
    url = f'{settings.MS_CLIENTES_URL}/api/v1/contratos/por-vencer/'
    data = _get(url)
    if data:
        contratos = data.get('results', data) if isinstance(data, dict) else data
        for c in contratos:
            fecha_fin = date.fromisoformat(c.get('fecha_fin', ''))
            dias_restantes = (fecha_fin - hoy).days
            mensaje = (
                f'El contrato {c.get("numero_contrato")} del cliente '
                f'{c.get("cliente_nombre")} vence en {dias_restantes} días ({fecha_fin}).'
            )
            nivel = NivelAlerta.CRITICAL if dias_restantes <= 7 else NivelAlerta.WARNING
            _, creada = _upsert_alerta(
                tipo=TipoAlerta.CONTRATO_POR_VENCER,
                nivel=nivel,
                cliente_id=c.get('cliente'),
                cliente_nombre=c.get('cliente_nombre', ''),
                contrato_id=c.get('id'),
                contrato_numero=c.get('numero_contrato', ''),
                mensaje=mensaje,
                datos_extra={
                    'fecha_fin': str(fecha_fin),
                    'dias_restantes': dias_restantes,
                }
            )
            if creada:
                generadas += 1

    logger.info('Alertas contratos procesadas. Nuevas: %d', generadas)
    return generadas


# ─────────────────────────────────────────────────────────────────────────────
# EJECUCIÓN COMPLETA
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_motor_alertas():
    """Corre todos los verificadores. Llamado por Celery Beat o manualmente."""
    total = 0
    total += verificar_alertas_toner()
    total += verificar_alertas_cuota()
    total += verificar_alertas_contratos()
    logger.info('Motor de alertas finalizado. Total nuevas alertas: %d', total)
    return total
