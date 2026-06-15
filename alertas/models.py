from django.db import models


class TipoAlerta(models.TextChoices):
    TONER_BAJO = 'TONER_BAJO', 'Tóner bajo'
    TONER_CRITICO = 'TONER_CRITICO', 'Tóner crítico'
    CUOTA_EXCEDIDA = 'CUOTA_EXCEDIDA', 'Cuota mensual excedida'
    CONTRATO_POR_VENCER = 'CONTRATO_POR_VENCER', 'Contrato por vencer'
    CONTRATO_VENCIDO = 'CONTRATO_VENCIDO', 'Contrato vencido'


class NivelAlerta(models.TextChoices):
    INFO = 'INFO', 'Informativo'
    WARNING = 'WARNING', 'Advertencia'
    CRITICAL = 'CRITICAL', 'Crítico'


class EstadoAlerta(models.TextChoices):
    ACTIVA = 'ACTIVA', 'Activa'
    RESUELTA = 'RESUELTA', 'Resuelta'
    IGNORADA = 'IGNORADA', 'Ignorada'


class Alerta(models.Model):
    """
    Alerta generada por el motor al detectar condiciones anómalas.
    Referencia IDs de ms-equipos y ms-clientes sin FK reales.
    """
    tipo = models.CharField(max_length=25, choices=TipoAlerta.choices)
    nivel = models.CharField(max_length=10, choices=NivelAlerta.choices)
    estado = models.CharField(max_length=10, choices=EstadoAlerta.choices, default=EstadoAlerta.ACTIVA)

    # Referencias a otros microservicios
    equipo_id = models.PositiveIntegerField(null=True, blank=True)
    equipo_nombre = models.CharField(max_length=200, blank=True)
    equipo_serial = models.CharField(max_length=100, blank=True)
    cliente_id = models.PositiveIntegerField(null=True, blank=True)
    cliente_nombre = models.CharField(max_length=200, blank=True)
    contrato_id = models.PositiveIntegerField(null=True, blank=True)
    contrato_numero = models.CharField(max_length=50, blank=True)

    # Datos específicos de la alerta
    mensaje = models.TextField()
    datos_extra = models.JSONField(default=dict, blank=True)

    # Resolución
    resuelta_en = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.CharField(max_length=150, blank=True)
    nota_resolucion = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        indexes = [
            models.Index(fields=['estado', 'nivel']),
            models.Index(fields=['equipo_id']),
            models.Index(fields=['cliente_id']),
        ]

    def __str__(self):
        return f'[{self.nivel}] {self.tipo} — {self.equipo_nombre or self.cliente_nombre}'


class ConfiguracionAlerta(models.Model):
    """
    Umbrales configurables para el motor de alertas.
    Se guarda como clave-valor para ser escalable.
    """
    clave = models.CharField(max_length=100, unique=True)
    valor = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    # Valores por defecto:
    # toner_warning_pct = 15
    # toner_critical_pct = 5
    # cuota_excedida_pct = 110   (110% de la cuota)
    # contrato_vencer_dias = 30

    class Meta:
        verbose_name = 'Configuración de alerta'
        verbose_name_plural = 'Configuraciones de alertas'

    def __str__(self):
        return f'{self.clave} = {self.valor}'

    @classmethod
    def get(cls, clave, default=None):
        try:
            return cls.objects.get(clave=clave).valor
        except cls.DoesNotExist:
            return default
