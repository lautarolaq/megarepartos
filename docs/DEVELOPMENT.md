# Development — Megarepartos

Cómo levantar el proyecto localmente.

## Requisitos

- **Python 3.12+** (el proyecto usa `from __future__ import annotations` + sintaxis 3.10+).
- **Node 20+** y npm.
- **Docker** + Docker Compose (para Postgres local).
- **make**.

## Setup inicial

```bash
git clone https://github.com/lautarolaq/megarepartos.git
cd megarepartos
cp .env.example .env
make install
```

`make install` crea el venv en `backend/.venv` e instala dependencias del frontend.

## Levantar el entorno

```bash
make dev
```

Esto:
1. Levanta Postgres en Docker (`localhost:5433` — el puerto estándar 5432 suele estar ocupado por otros Postgres / tuneles IAP).
2. Arranca backend con uvicorn en `http://localhost:8000`.
3. Arranca frontend con Vite en `http://localhost:5173`.

`Ctrl+C` corta los tres.

## Migraciones

```bash
make migrate                                 # alembic upgrade head
make migration-new m="agrega columna X"      # crea revisión autogenerada
```

## Tests

```bash
make test            # toda la suite
make test-fast       # unit + integration, saltea e2e
make test-unit
make test-integration
```

> En TASK-000 la suite arranca vacía. Los tests reales se agregan a medida que
> aterricen TASKs (cada feature trae sus tests, regla CLAUDE.md Tests #1).

## Lint y formato

```bash
make lint       # ruff + mypy + biome
make lint-fix   # aplica fixes automáticos
```

## Smoke checks

```bash
curl http://localhost:8000/health
# → {"status": "ok", "db": "ok"}
```

## Variables de entorno

Ver `.env.example`. Las críticas en local:

- `DATABASE_URL` — connection string async. Default apunta al Postgres de Docker.
- `JWT_SECRET` — cualquier string, se regenera en cada entorno.
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` — necesarios para que el
  flow de login real funcione. Tests pasan sin estos (mockean Google). Para
  desarrollo end-to-end:
  1. Ir a https://console.cloud.google.com/apis/credentials.
  2. Crear OAuth 2.0 Client ID (Web application).
  3. Authorized redirect URIs: `http://localhost:8000/api/auth/google/callback`.
  4. Copiar Client ID + Secret a `.env`.

En prod las completa Secret Manager.

## Estructura del repo

Ver `docs/MEGAREPARTOS_SPEC.md` sección 17.

## Workflow de cambios

1. Crear (o pedir) `tareas/TASK-XXX.yaml`.
2. `git checkout -b feature/TASK-XXX-descripcion-corta`.
3. Implementar + tests.
4. `make lint && make test` localmente.
5. Push + PR a `main`. CI tiene que pasar todo antes de mergear.

## Troubleshooting

### `make dev` no encuentra Docker

Levantar Docker Desktop primero.

### `make migrate` falla con `connection refused`

Verificar que `make dev-db` levantó Postgres: `docker compose ps`. Si no
aparece el contenedor, `docker compose up -d db`.

### Test/lint usan otro Python

Confirmar que `backend/.venv/bin/python --version` es 3.12+. Si no, borrar venv:
`rm -rf backend/.venv && make install-backend`.
