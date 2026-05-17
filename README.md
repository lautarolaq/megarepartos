# Megarepartos

Plataforma SaaS de campañas de WhatsApp para negocios de reparto recurrente
(soderías, garrafas, viandas, distribuidoras).

> **Estado**: en construcción. Sprint 0 — setup técnico.

## Stack

- **Backend**: Python 3.12 · FastAPI · SQLAlchemy 2 async · Alembic · Pydantic v2 · Postgres (Neon en prod).
- **Frontend**: Vite · React 18 · TypeScript · Tailwind · TanStack Query · Zustand.
- **Extensión Chrome**: Manifest V3 · TypeScript · webpack.
- **Infra**: Cloud Run · Cloud Storage · GitHub Actions.

## Estructura

```
megarepartos/
├── backend/            # FastAPI + SQLAlchemy + Alembic
├── frontend/           # App web (admin/operador) + página pública del link
├── extension/          # Extensión Chrome (TASK posterior)
├── behaviors/          # REQ-IDs como specs ejecutables
├── tareas/             # TASK-XXX.yaml — unidad de trabajo
├── scripts/            # Checks de arquitectura, coverage, etc.
├── docs/               # SPEC, arquitectura, runbooks
└── .github/workflows/  # CI/CD
```

Detalles completos en `docs/MEGAREPARTOS_SPEC.md` (sección 17).

## Desarrollo local

Requisitos: Python 3.12, Node 20+, Docker.

```bash
# Levantar Postgres + backend + frontend
make dev

# Tests
make test

# Lint
make lint
```

Ver `docs/DEVELOPMENT.md` para detalle.

## Documentación

- `docs/MEGAREPARTOS_SPEC.md` — especificación completa (producto, filosofía, operación).
- `docs/ARCHITECTURE.md` — decisiones técnicas detalladas.
- `docs/DEVELOPMENT.md` — cómo desarrollar localmente.
- `CLAUDE.md` — reglas no negociables para Claude Code.

## Licencia

Propietario. Todos los derechos reservados.
