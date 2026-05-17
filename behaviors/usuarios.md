# Usuarios — REQ-IDs

## Contexto

Gestión de usuarios DENTRO de la empresa. La creación de usuarios pasa SOLO
por OAuth (TASK-001/002) — este TASK cubre listar, cambiar rol y desactivar.

## Requisitos

### REQ-USR-001
`GET /api/usuarios` lista los usuarios de la empresa del JWT, ordenados por
`nombre ASC`.

### REQ-USR-002
`?activo=true|false` filtra.

### REQ-USR-003
`GET /api/usuarios/{id}` ajeno devuelve 404.

### REQ-USR-004
`PATCH /api/usuarios/{id}` permite cambiar `rol` y `activo` (admin only).

### REQ-USR-005
PATCH con `rol` distinto de `"admin"` o `"operador"` devuelve 400.

### REQ-USR-006
PATCH/DELETE como operador devuelven 403.

### REQ-USR-007
`DELETE /api/usuarios/{id}` desactiva (soft, `activo=false`).

### REQ-USR-008
Admin NO puede desactivarse a sí mismo (DELETE o PATCH `activo=false` sobre
su propio id) → 409 `CONFLICTO_ESTADO`. Evita lockout.

### REQ-USR-009
Cada PATCH/DELETE genera `EventoDominio` con `entidad_tipo="usuario"`.

## No-requisitos

- No hay endpoint para crear usuarios. La creación pasa por OAuth (TASK-001).
- No se pueden modificar email, google_oauth_token, empresa_id, fecha_creacion.
- Flujo de invitación con magic link es TASK posterior (necesita email
  transaccional).
