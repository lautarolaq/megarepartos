# Auth — REQ-IDs

## Contexto

Autenticación de usuarios via Google OAuth (Authorization Code Flow). Crítico
para multi-tenant porque define la identidad (`usuario_id`, `empresa_id`, `rol`)
de cada request.

JWT-based: access tokens cortos (60 min default) + refresh tokens largos (14 días
default) en cookie HTTP-only. Claims firmados con `JWT_SECRET` (HS256).

## Requisitos

### REQ-AUTH-001

`GET /api/auth/google/url` devuelve `{"url": "https://accounts.google.com/..."}`
con la URL de autorización de Google. El parámetro `state` está firmado por
el backend (HMAC sobre un nonce) para evitar CSRF.

### REQ-AUTH-002

`GET /api/auth/google/callback?code=&state=` con `code` válido y `state` firmado:
- Intercambia code con Google → recibe `id_token`, `access_token`, `refresh_token`.
- Verifica `id_token` con la JWKS de Google.
- Llama a `login_or_create_user(sub, email, name)` (REQ-EMP-001).
- Setea cookie `mr_refresh` (HTTP-only, SameSite=Lax, Secure en prod).
- Redirige al frontend con el access token en query string (vida muy corta — el
  frontend lo guarda en memoria al cargar y limpia la URL).

### REQ-AUTH-003

Callback con `state` inválido (firma incorrecta o expirada) devuelve 400 con
`error.code = "VALIDACION_INPUT"`.

### REQ-AUTH-004

`POST /api/auth/refresh` con cookie `mr_refresh` válida devuelve
`{"access_token": "...", "token_type": "bearer", "expires_in": <segundos>}`.

### REQ-AUTH-005

`POST /api/auth/refresh` sin cookie `mr_refresh` devuelve 401 con
`error.code = "AUTH_REQUIRED"`.

### REQ-AUTH-006

`POST /api/auth/refresh` con cookie expirada o firma inválida devuelve 401 con
`error.code = "AUTH_INVALID"`.

### REQ-AUTH-007

`POST /api/auth/logout` con cookie `mr_refresh` devuelve 204 y borra la cookie
(`Set-Cookie: mr_refresh=; Max-Age=0`). Sin cookie, también devuelve 204
(operación idempotente).

### REQ-AUTH-008

`GET /api/auth/me` con `Authorization: Bearer <access_token>` válido devuelve
`{"usuario": {id, email, nombre, rol, ...}, "empresa": {id, nombre, ...}}`.

### REQ-AUTH-009

`GET /api/auth/me` sin header `Authorization` devuelve 401 con
`error.code = "AUTH_REQUIRED"`.

### REQ-AUTH-010

`GET /api/auth/me` con token expirado, mal firmado o con `type != "access"`
devuelve 401 con `error.code = "AUTH_INVALID"`.

### REQ-AUTH-011

Access tokens expiran en `JWT_ACCESS_TTL_MIN` minutos (default 60).
Refresh tokens expiran en `JWT_REFRESH_TTL_DAYS` días (default 14).

### REQ-AUTH-012

El payload de cada JWT incluye estos claims:
- `sub`: UUID del usuario (string).
- `empresa_id`: UUID de la empresa (string).
- `rol`: `"admin"` | `"operador"`.
- `type`: `"access"` | `"refresh"`.
- `exp`: timestamp UNIX de expiración.
- `iat`: timestamp UNIX de emisión.

## No-requisitos

- No soporta login con email/password (sólo Google OAuth).
- No emite tokens si `Usuario.activo = false` (ver REQ-EMP-006).
- No persiste tokens de Google más allá de `usuario.google_oauth_token` (que
  se cifra en TASK posterior).

## Notas de implementación

- El `state` se firma con HMAC-SHA256 sobre `{nonce}.{timestamp}` con
  `JWT_SECRET` como clave. TTL del `state`: 10 minutos.
- La verificación del id_token usa `google.oauth2.id_token.verify_oauth2_token`
  (librería `google-auth` de la lista blanca).
- En tests, el verificador se mockea (no hacemos calls reales a Google).
