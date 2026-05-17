# Productos (catálogo) — REQ-IDs

## Contexto

Primera entidad CRUD de la app. Cada empresa tiene su catálogo: bidón 20L,
soda 1.5L, agua mineral 500ml, etc. Los productos se referencian desde
`producto_habitual` (cliente → cantidad habitual) y desde
`confirmacion_pedido` (qué pidió cada cliente).

Sólo `admin` puede modificar el catálogo. Operadores ven el catálogo
read-only (no cubrimos lectura por rol en este TASK — todos los autenticados
leen; las escrituras requieren admin).

## Requisitos

### REQ-PROD-001

`GET /api/productos` devuelve `{items: [...]}` solo con los productos de
la empresa del JWT, ordenados por `(orden_display ASC, nombre ASC)`.

### REQ-PROD-002

`GET /api/productos?activo=true` filtra por `activo=true`. Sin el query
param, devuelve todos (activos + inactivos). `?activo=false` devuelve
solo inactivos.

### REQ-PROD-003

`GET /api/productos/{id}` con id de empresa ajena devuelve 404 con
`error.code = "RECURSO_NO_ENCONTRADO"`. NO 403 (no leakeamos la existencia
del ID en otra empresa).

### REQ-PROD-004

`POST /api/productos` crea el producto en la empresa del JWT. Devuelve
201 con el `ProductoOut`.

### REQ-PROD-005

`POST /api/productos` sin `nombre` (o nombre vacío) devuelve 400 con
`error.code = "VALIDACION_INPUT"`.

### REQ-PROD-006

`POST /api/productos` como `operador` (rol del JWT) devuelve 403
`PERMISO_DENEGADO`.

### REQ-PROD-007

`PATCH /api/productos/{id}` actualiza solo los campos enviados. Los
no-enviados no se tocan (semántica PATCH estándar).

### REQ-PROD-008

`PATCH /api/productos/{id}` de empresa ajena devuelve 404.

### REQ-PROD-009

`DELETE /api/productos/{id}` hace **soft delete**: pone `activo=false`.
Devuelve 204.

### REQ-PROD-010

`DELETE /api/productos/{id}` es **idempotente**: borrar un producto ya
desactivado devuelve 204 también. El producto sigue con `activo=false`.

### REQ-PROD-011

Cada POST/PATCH/DELETE genera un `evento_dominio`:
- POST: `entidad_tipo="producto"`, `accion="creado"`, `detalles` con
  el snapshot inicial.
- PATCH: `accion="modificado"`, `detalles` con diff de campos cambiados.
- DELETE: `accion="desactivado"`, `detalles` vacío.

### REQ-PROD-012

`POST /api/productos` con `envase_id` cuyo envase no pertenece a la
empresa del JWT (o no existe) devuelve 422 con
`error.code = "VALIDACION_SEMANTICA"`. Defensa contra crear productos
con FK a envases ajenos.

## No-requisitos

- No hay endpoint de "hard delete" — soft delete siempre.
- No hay endpoint de "reactivar" en este TASK. Si un admin necesita
  reactivar, lo hace vía `PATCH {activo: true}`.
- No hay búsqueda por nombre (`?q=...`) en este TASK. Se agrega en TASK
  futuro si aparece el pedido.

## Notas de implementación

- Los listados usan paginación implícita: devuelven hasta 200 items.
  Si la sodería supera 200 productos (improbable), se agrega paginación
  explícita.
- `orden_display` permite que la empresa reordene el catálogo para que
  los productos más vendidos aparezcan primero en pantallas operativas.
- El campo `precio_unitario_default` es opcional y se usa para sugerir
  precios al armar listas; las cobranzas calculan en base a otra fuente.
