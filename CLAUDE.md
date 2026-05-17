# CLAUDE.md — Reglas del proyecto Megarepartos

## Contexto

Megarepartos es una plataforma de campañas de WhatsApp para negocios de reparto recurrente.
Backend Python (FastAPI + SQLAlchemy 2 async + Postgres).
Frontend React (Vite + TS + Tailwind).
Extensión Chrome propia que controla WhatsApp Web del usuario.

La especificación completa está en `docs/MEGAREPARTOS_SPEC.md`. Léela si necesitás contexto
sobre arquitectura, modelo de datos, o flujos.

## Workflow

1. Toda feature nueva nace como `tareas/TASK-XXX.yaml`.
2. Si no existe el TASK.yaml, pedímelo antes de codear.
3. Trabajá en una rama `feature/TASK-XXX-descripcion-corta`.
4. Al terminar, abrí PR. CI tiene que pasar todo.
5. Si CI rompe, debuggá y arreglalo antes de pedir review.

## Reglas no negociables

### Backend

1. **Multi-tenancy SIEMPRE**: toda query a tablas de negocio filtra por `empresa_id` del
   usuario logueado. Sin excepciones. Si no podés filtrar (caso público con token), justificalo
   en el código con un comentario explícito.

2. **Toda operación de escritura usa `event_recorder`**: importá desde `domain/_events.py`
   y envolvé la operación. Genera el `evento_dominio` automáticamente.

3. **Mutaciones de mensajes enviados solo desde `domain/campanas.py`**: ningún otro archivo
   puede hacer INSERT en `mensaje_enviado`. Si necesitás registrar un envío, llamá a la
   función correspondiente.

4. **Tokens firmados solo desde `domain/tokens.py`**: generación, validación y revocación.

5. **API solo en `api/*.py`, lógica solo en `domain/*.py`**: los endpoints validan input
   y delegan. Nada de lógica de negocio en endpoints.

6. **`api/*.py` NO importa de `models/`**: solo de `domain/`, `schemas/`, `infra/auth`.

7. **`domain/*.py` NO importa de `api/` ni `schemas/`**: es lógica pura.

8. **Async siempre**: FastAPI + SQLAlchemy 2 async. Nada de DB calls sincrónicos.

9. **Idempotencia en endpoints críticos**: POST `/api/campanas/{id}/enviar` y similares
   aceptan header `Idempotency-Key` y dedupean.

10. **Errores con códigos estándar**: 400 (validación), 401 (no auth), 403 (sin permiso),
    404 (no existe), 409 (conflicto), 422 (semántico), 500 (server). Body siempre
    `{error: {code, message, details}}`.

11. **Página pública del link**: NO requiere auth pero valida token firmado.
    Endpoint `/api/publico/c/{token}` es la única excepción a multi-tenancy normal.

12. **Comunicación con la extensión**: endpoints en `/api/extension/*` requieren
    `X-Extension-Token` header válido.

### Frontend

1. **TanStack Query para todo lo que viene del server**: nada de `useEffect + fetch`.
2. **Zustand solo para estado cliente**: nunca para datos del server.
3. **Tailwind solo, sin CSS modules ni styled-components**.
4. **Componentes UI reusables en `components/ui/`**: Button, Input, Modal, etc. Variantes vía props.
5. **Mobile-first para `pages/publico/*`**: viewport 375px como base.
6. **Google OAuth via `lib/google.ts`**: nunca llamar SDK directo desde componentes.
7. **Variables de campañas resueltas en backend**: frontend nunca renderiza placeholders.

### Extensión

1. **Selectores DOM centralizados en `content/selectors.ts`**: nunca hardcoded en otros archivos.
2. **Delays aleatorios obligatorios**: nunca enviar dos mensajes sin pausa de 3-8s.
3. **Validación contra backend en cada envío**: si falla, detener inmediatamente.
4. **No leer cookies fuera de WhatsApp Web y Megarepartos**: privacy.
5. **Sin telemetría externa**: solo nuestro backend.

### Tests

1. **Toda feature tiene test**: si tocás `domain/X.py` o `api/X.py`, tenés que tocar
   `tests/.../test_X.py`.
2. **REQ-IDs del `behaviors/X.md` se mapean a tests vía `@pytest.mark.req("REQ-X-001")`**.
3. **Tests de integración corren contra Postgres real** (testcontainer).
4. **Property-based tests para invariantes**: usar hypothesis.
5. **Mínimo en cada API endpoint**: 1 happy path + 1 auth + 1 aislamiento multi-tenant.
6. **Bug fixes requieren test de regresión** en `tests/regression/`.

### Dependencias

1. **No agregar librerías sin justificación**: si necesitás una nueva, explicala en el PR.
2. **Lista blanca** (puedo agregar otras con justificación):
   - **Backend**: fastapi, sqlalchemy, alembic, pydantic, pydantic-settings, structlog,
     httpx, pytest, pytest-asyncio, hypothesis, factory-boy, testcontainers, asyncpg,
     python-jose, python-multipart, google-auth, google-api-python-client, mercadopago.
   - **Frontend**: react, react-dom, react-router-dom, @tanstack/react-query, zustand,
     axios, date-fns, lucide-react, vite-plugin-pwa, react-hook-form, zod, @headlessui/react.
   - **Extensión**: webpack, typescript, react (popup), zod.

## Commits

Convención: `tipo(scope): mensaje` en español.

- `feat(campanas): agrega endpoint POST /api/campanas/{id}/enviar`
- `fix(matching): corrige fuzzy matching cuando hay tildes`
- `test(cobranzas): cubre REQ-COBR-007`
- `docs(spec): actualiza sección 9`
- `chore(deps): actualiza fastapi`

## Comandos canónicos

- `make dev`: arranca backend + frontend local con Postgres en Docker.
- `make test`: corre todos los tests.
- `make test-fast`: corre unit + integration, skipea E2E.
- `make lint`: ruff + mypy + biome.
- `make health`: smoke test completo.
- `make integrity`: validaciones de integridad sobre DB local.
- `make security-check`: aislamiento multi-tenant.
- `make seed-demo`: carga data demo en DB local.
- `make migrate`: alembic upgrade head.
- `make migration-new "descripcion"`: alembic revision --autogenerate.
- `make extension-dev`: arranca extensión en modo dev (watch mode).
- `make extension-build`: build de producción de la extensión.

## Catálogo de errores estándar

Códigos de error que retorna la API. Definir constantes en `infra/errors.py`.

- `AUTH_REQUIRED`: 401 — no se proveyó token.
- `AUTH_INVALID`: 401 — token inválido o expirado.
- `PERMISO_DENEGADO`: 403 — usuario sin permiso para esta acción.
- `RECURSO_NO_ENCONTRADO`: 404 — entidad no existe o no pertenece a tu empresa.
- `VALIDACION_INPUT`: 400 — body o query params mal formados.
- `VALIDACION_SEMANTICA`: 422 — input válido pero viola regla de negocio.
- `CONFLICTO_ESTADO`: 409 — operación no válida en el estado actual.
- `LIMITE_PLAN`: 402 — superó el límite de su plan.
- `RATE_LIMIT`: 429 — demasiadas requests.
- `EXTERNO_FALLO`: 503 — falló dependencia externa (Google, MercadoPago).
- `INTERNO`: 500 — error inesperado del servidor.

## Cuando dudes

Si tenés duda sobre una decisión de diseño, **preguntá antes de implementar**. Mejor
5 minutos de pregunta que 2 horas de rehacer.

Especialmente preguntá si:
- La feature parece ambigua respecto al SPEC.
- Una dependencia nueva podría ser útil.
- Hay tradeoff entre simplicidad y robustez.
- Una decisión podría afectar la performance o el costo de infra.
