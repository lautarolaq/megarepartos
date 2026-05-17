# Architecture — Megarepartos

> Decisiones técnicas detalladas. Complementa a `MEGAREPARTOS_SPEC.md` (que es la
> fuente de verdad de producto y reglas de alto nivel). Acá se anotan **decisiones
> técnicas concretas** que pueden cambiar sin afectar el producto.

## Estado

TASK-000 sólo deja en pie el andamiaje: estructura de carpetas, conexión a DB,
`/health`, schema inicial completo, frontend stub. Las decisiones de auth,
multi-tenant middleware, repositorios, etc. se documentan a medida que aterricen
en TASKs siguientes.

## Stack actual

- Backend: Python 3.12 + FastAPI + SQLAlchemy 2 async + asyncpg + Alembic + Pydantic v2.
- Frontend: Vite + React 18 + TS + Tailwind. Sin router por ahora (TASK-001+).
- DB: Postgres 16 (local via Docker; Neon en prod).
- Logging: structlog → stdout → Cloud Logging.

## Layout de carpetas

Ver sección 17 del SPEC. Reglas no negociables:

- `backend/src/megarepartos/api/` NO importa `models/`.
- `backend/src/megarepartos/domain/` NO importa `api/` ni `schemas/`.
- `backend/src/megarepartos/models/` no importa nada del proyecto.

Estas reglas se enforcean vía `scripts/check_arquitectura.py` en CI.

## Multi-tenant (a implementar en TASK-003)

- Toda tabla de negocio tiene `empresa_id` con FK a `empresa.id`.
- RLS de Postgres filtra por `empresa_id` de la sesión.
- Repositorios inyectan `empresa_id` automáticamente.
- Tests de aislamiento por endpoint son obligatorios.

## Conexión a DB

`backend/src/megarepartos/infra/db.py` expone un `engine` global y `get_session`
como dependency FastAPI. Pool default: 5 conexiones, 10 overflow. Para Cloud
Run hay que validar estos números con tráfico real.

## Migraciones

Una sola migración en `0001_schema_inicial.py` crea todo el schema de la sección
5 del SPEC. Las siguientes migraciones agregan tablas o columnas a medida que
aterricen los TASKs. **Nunca rollback de migraciones en producción** (forward-only).

## Pendiente de documentar

- Estrategia de auth (TASK-001).
- RLS y multi-tenant middleware (TASK-003).
- Patrón de repositorios (TASK-004).
- `event_recorder` y `evento_dominio` (TASK-005).
- Sistema de tokens firmados (TASK-021).
- Comunicación backend ↔ extensión (TASK-037).
