# ms-alertas — PrintControl

Motor de alertas que consume ms-equipos y ms-clientes para generar
alertas de tóner bajo, cuota excedida y contratos por vencer.

## Arquitectura

```
ms-equipos (8001) ──┐
                    ├──► ms-alertas (8003) ──► PostgreSQL + Redis + Celery
ms-clientes (8002) ─┘
```

## Tipos de alerta

| Tipo | Nivel | Condición |
|------|-------|-----------|
| TONER_BAJO | WARNING | Tóner ≤ 15% |
| TONER_CRITICO | CRITICAL | Tóner ≤ 5% |
| CUOTA_EXCEDIDA | WARNING | Ciclos mes ≥ 110% de cuota |
| CONTRATO_POR_VENCER | WARNING/CRITICAL | Contrato vence en ≤ 30 días |

Los umbrales son configurables via `/api/v1/configuracion/`.

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/alertas/` | Todas las alertas |
| GET | `/api/v1/alertas/activas/` | Solo alertas activas |
| GET | `/api/v1/alertas/resumen/` | Métricas para dashboard |
| POST | `/api/v1/alertas/{id}/resolver/` | Marcar como resuelta |
| POST | `/api/v1/alertas/{id}/ignorar/` | Ignorar alerta |
| POST | `/api/v1/alertas/ejecutar-motor/` | Correr motor manualmente |
| GET/POST | `/api/v1/configuracion/` | Umbrales configurables |
| GET | `/api/docs/` | Swagger UI |

## Levantar con Docker

```bash
cd ms-alertas

# Windows PowerShell
Copy-Item .env.example .env

docker-compose up --build
```

Accede a:
- API: http://localhost:8003/api/v1/
- Swagger: http://localhost:8003/api/docs/
- Admin: http://localhost:8003/admin/

## Prueba rápida — ejecutar motor manualmente

```bash
curl -X POST http://localhost:8003/api/v1/alertas/ejecutar-motor/
```

## Configurar umbrales

```bash
# Bajar el umbral de alerta de tóner a 20%
curl -X POST http://localhost:8003/api/v1/configuracion/ \
  -H "Content-Type: application/json" \
  -d '{
    "clave": "toner_warning_pct",
    "valor": "20",
    "descripcion": "Alerta cuando el tóner baja de este porcentaje"
  }'
```
