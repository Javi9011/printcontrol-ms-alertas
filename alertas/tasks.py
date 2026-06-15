import logging
from celery import shared_task
from .services import ejecutar_motor_alertas

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='alertas.tasks.verificar_todas_las_alertas')
def verificar_todas_las_alertas(self):
    """
    Tarea periódica que ejecuta el motor de alertas completo.
    Configurada para correr cada hora via django-celery-beat.
    """
    try:
        total = ejecutar_motor_alertas()
        return {'status': 'ok', 'nuevas_alertas': total}
    except Exception as exc:
        logger.error('Error en tarea de alertas: %s', exc)
        raise self.retry(exc=exc, countdown=60, max_retries=3)
