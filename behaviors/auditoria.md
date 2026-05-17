# Auditoría — REQ-IDs

## Contexto

Toda operación de escritura genera un `EventoDominio` (regla CLAUDE.md
Backend #2). El registro tiene `entidad_tipo`, `accion`, `detalles_jsonb`
+ contexto del request (`request_id`, `ip_origen`, `user_agent`).

El flujo:

1. `AuditContextMiddleware` corre antes que cualquier endpoint, captura
   request_id (UUID generado, o `X-Request-ID` si el cliente lo manda),
   IP, User-Agent, y los expone vía `contextvars`.
2. El endpoint llama a domain functions que usan `event_recorder` (context
   manager). El recorder lee las contextvars y arma el `EventoDominio`.
3. Al salir del `async with`, el evento se persiste (en la misma transacción
   que la operación — si rollback, el evento también).

## Requisitos

### REQ-AUD-001

`AuditContextMiddleware`:
- Genera `request_id` con `uuid.uuid4()` si el request no manda
  `X-Request-ID` header.
- Captura `request.client.host` como ip_origen.
- Captura `User-Agent` header (truncado a 512 chars para que entre en la
  columna).
- Expone los tres vía contextvars (`current_request_id`,
  `current_ip_origen`, `current_user_agent`).
- En la respuesta inyecta `X-Request-ID: <uuid>` para correlación cliente↔servidor.

### REQ-AUD-002

Cuando `event_recorder` persiste, lee las contextvars y llena
`EventoDominio.ip_origen` y `EventoDominio.user_agent`.

### REQ-AUD-003

`EventoDominio.detalles_jsonb` siempre incluye `request_id` cuando hay
contexto (`detalles_jsonb["request_id"] = "<uuid>"`).

### REQ-AUD-004

Si el código corre fuera de un request (cron, test directo, script de
migración con seed), las contextvars devuelven None. `event_recorder`
persiste el evento con `ip_origen = NULL` y `user_agent = NULL`. No falla.

### REQ-AUD-005

`event_recorder` requiere `empresa_id` como argumento obligatorio. Si el
caller no lo provee, levanta `ApiError(INTERNO, "evento sin empresa_id")`.
Esto previene eventos huérfanos sin tenant context (defensa contra bugs).

## No-requisitos

- No persistimos `Authorization` ni cookies en `user_agent`. Solo el header
  `User-Agent` clásico.
- No correlacionamos logs técnicos (structlog) con eventos de dominio
  en este TASK — eso se hace en TASK posterior con el `request_id`
  como llave común.

## Notas de implementación

- Las contextvars usan `contextvars.ContextVar` (stdlib). FastAPI/Starlette
  manejan el contexto por request automáticamente.
- El middleware se monta antes que los routers para garantizar que toda
  request pasa por él.
- En tests sin HTTP (unit tests que llaman a domain functions directo),
  las contextvars no se setean — el helper persiste igual con nulls.
