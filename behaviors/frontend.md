# Frontend base — REQ-IDs

## Contexto

App web con Vite + React 18 + Tailwind. Stack según CLAUDE.md sección
Frontend: TanStack Query para server state, Zustand para client state,
Tailwind para estilos.

## Requisitos

### REQ-FE-001
`GET /` redirige a `/login` si no hay `access_token` en Zustand. Si hay, va a
`/dashboard`.

### REQ-FE-002
`GET /auth/callback` extrae `access_token` del fragmento (`window.location.hash`),
lo guarda en Zustand y redirige a `/dashboard`. El hash se limpia para que el
token no quede en la URL visible.

### REQ-FE-003
El cliente axios (`lib/api.ts`) tiene un interceptor que agrega
`Authorization: Bearer <access_token>` automáticamente si Zustand lo tiene.

### REQ-FE-004
Si una request devuelve 401, el interceptor llama a `POST /api/auth/refresh`
(usa la cookie HTTP-only). Si responde con nuevo access, retry la request
original. Si falla, limpia Zustand y redirige a `/login`.

### REQ-FE-005
`/dashboard/productos`:
- Lista paginada de productos.
- Botón "Nuevo producto" → modal con form (nombre, descripcion, precio, retornable, orden).
- Cada item tiene íconos para editar y borrar (soft delete).

### REQ-FE-006
`/dashboard/clientes`:
- Lista paginada con búsqueda `q=` (debounced ~300ms).
- Filtros por modalidad y activo (selects).
- Botón "Nuevo cliente" → modal con form.

### REQ-FE-007
"Cerrar sesión": POST `/api/auth/logout` + limpia Zustand + redirige a `/login`.

## No-requisitos

- No hay edición inline en las listas (siempre via modal). UX más sofisticada
  es TASK posterior.
- No hay filtros avanzados en la lista de productos (solo activo).
- Sin PWA / service worker en este TASK (vite-plugin-pwa configurable después).
- Sin tests E2E con Playwright todavía (TASK del Sprint 10 o cuando aparezca un bug visual).

## Notas

- El access_token vive solo en memoria (Zustand). Si el usuario refresca la
  página, pierde el token y debe re-loguearse (el refresh cookie lo evita
  parcialmente — un boot fetch a `/api/auth/refresh` puede recuperar la sesión
  silenciosamente; se implementa en TASK posterior).
- Toda llamada a server pasa por `lib/api.ts`. No hay `fetch()` crudo.
