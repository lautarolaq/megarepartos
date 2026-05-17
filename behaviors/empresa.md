# Empresa + Usuario (primer login) — REQ-IDs

## Contexto

Cuando un usuario hace login con Google por primera vez, no existe ni
`Usuario` ni `Empresa`. El flow de auth llama a `login_or_create_user` que
resuelve el caso.

Multi-tenant real (RLS, repositorios con `empresa_id` automático, aislamiento)
viene en TASK-003+. Acá solo habilitamos el primer-login para que el flow de
OAuth pueda emitir JWTs.

## Requisitos

### REQ-EMP-001

`domain.auth.login_or_create_user(session, google_sub, email, nombre)` con email
que no existe en `usuario`:
- Crea una `Empresa` con `nombre = f"Empresa de {nombre}"`,
  `tipo_negocio = "otro"`, `estado_suscripcion = "trial"`.
- Crea un `Usuario` asociado, con `rol = "admin"`, `activo = true`,
  `google_oauth_token = None` (se completa en TASK posterior).
- Devuelve `(empresa, usuario)`.

### REQ-EMP-002

El email se normaliza a lowercase antes de buscar/crear. Es decir:
`login_or_create_user(..., email="Foo@Bar.com", ...)` crea un usuario con
`usuario.email = "foo@bar.com"` y un segundo login con `"foo@bar.com"`
encuentra el mismo registro.

### REQ-EMP-003

`login_or_create_user` con email que ya existe:
- Actualiza `usuario.ultima_sesion` a `now()`.
- Devuelve la `(Empresa, Usuario)` existente.
- No crea nada nuevo.

### REQ-EMP-004

`Empresa` creada inicializa con:
- `estado_suscripcion = "trial"`
- `timezone = "America/Argentina/Cordoba"`
- `tipo_negocio = "otro"` (placeholder; el onboarding wizard lo cambia)

### REQ-EMP-005

`Usuario` creado inicializa con:
- `rol = "admin"` (es el primer y único miembro)
- `activo = true`
- `email` en lowercase

### REQ-EMP-006

Si el `Usuario` existe pero está `activo = false`, `login_or_create_user`
levanta `ApiError(CONFLICTO_ESTADO)`. El handler de FastAPI lo mapea a HTTP 409.

### REQ-EMP-007

`PATCH /api/empresa/me` (admin) permite actualizar `nombre`, `tipo_negocio`,
`direccion_deposito` y `timezone` de la empresa del JWT. Cambios persistidos
como `evento_dominio` con `entidad_tipo="empresa"`, `accion="modificada"`.

### REQ-EMP-008

`GET /api/empresa/me` (cualquier rol autenticado) devuelve la empresa
del JWT con campos públicos (sin `plan_id`, sin `config_jsonb`).

## No-requisitos

- No soporta invitar usuarios a una empresa existente (TASK-012).
- No soporta un usuario con el mismo email en empresas distintas (futuro).
- No expone endpoint público para crear empresas — sólo se crean via OAuth.
- No setea `plan_id` (TASK-052 maneja planes).

## Notas de implementación

- Concurrencia: usamos `SELECT ... FOR UPDATE` sobre `usuario.email` antes de
  crear, dentro de la misma transacción. Si dos requests llegan en paralelo,
  el segundo ve el registro creado por el primero.
- Auditoría: la creación de Empresa y Usuario genera evento de dominio
  (TASK-005 cierra esto; en este TASK queda registrado el llamado pero el
  event_recorder es stub).
