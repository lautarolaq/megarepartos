# Link público del cliente — REQ-IDs

## Contexto

"Motor 2" del producto: cliente recibe un link único por WhatsApp, lo abre
en mobile, responde. Stateless: el token firmado lleva el `cliente_id` +
expiración. No requiere lookup en DB para validar.

Esta versión es la base mínima end-to-end. El template completo "confirmar
pedido con +/- por producto" (sección 6.5 del SPEC) se expande en TASK-023.

## Requisitos

### REQ-LINK-001
`sign_link_token(cliente_id, ttl_dias=30) -> str`. Formato:
`<cliente_id>.<ts>.<sig>` donde `sig = HMAC-SHA256(secret, cliente_id.ts)`.

### REQ-LINK-002
`verify_link_token(token) -> uuid.UUID`. Valida firma + TTL. Devuelve el
`cliente_id` o levanta `ApiError(VALIDACION_INPUT)` si algo falla.

### REQ-LINK-003
`GET /api/publico/c/{token}` (sin auth) devuelve:
```json
{
  "empresa": {"nombre": "..."},
  "cliente": {"nombre_completo": "...", "telefono": "..."}
}
```

### REQ-LINK-004
GET con token mal firmado o expirado devuelve 400 `VALIDACION_INPUT`.

### REQ-LINK-005
`POST /api/publico/c/{token}/respuesta` con body
`{"accion": "confirmo"|"rechazo", "datos": {...}}` devuelve 200 con `{ok: true}`.
Por ahora loggea — la persistencia en `respuesta_link` requiere
`mensaje_enviado_id` que viene de TASK-026 (campañas).

### REQ-LINK-006
Frontend `/c/:token` es **mobile-first**:
- Viewport 375px base.
- Botones de respuesta ≥60×60px.
- Nombre del cliente + nombre de la empresa grandes.
- Sin nav, sin login, sin sidebar — pantalla completa al servicio del cliente.

### REQ-LINK-007
Después de SÍ/NO, muestra pantalla de confirmación ("Listo Juan, mañana pasamos").

### REQ-LINK-008
`POST /api/clientes/{id}/generar-link` (admin only) devuelve
`{"url": "http://localhost:5173/c/<token>"}` para que el admin lo pegue en WhatsApp
manualmente (hasta que la extensión Chrome envíe automáticamente).

## No-requisitos

- No persistir la respuesta del cliente en este TASK (necesita `mensaje_enviado`
  que viene de Sprint 5).
- No mostrar productos habituales (eso es TASK-023, "confirmar pedido" con +/-).
- No expirar tokens revocados / lista negra. Stateless: TTL alcanza.
- No mobile detection / device-specific UI — mobile-first responsive sirve para
  todos los devices.

## Notas

- Token usa HMAC-SHA256 con `JWT_SECRET`. Mismo patrón que `sign_state` pero
  con cliente_id en el payload.
- El secret rotación invalida todos los tokens previos (deseable: si hay un
  leak, rotar y todos los links públicos expiran).
- La URL base del frontend para el link viene de Settings (configurable por
  entorno).
