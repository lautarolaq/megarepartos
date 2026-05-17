# Clientes — REQ-IDs

## Contexto

Clientes es la entidad central del producto. Cada sodería gestiona 100-2000.

## Requisitos

### REQ-CLI-001
`GET /api/clientes` devuelve `{items: [...], total: N, limit: L, offset: O}` con paginación:
- `?limit=50` default, máximo 200.
- `?offset=0` default.
- Ordenados por `nombre_completo ASC, id ASC`.

### REQ-CLI-002
`?q=texto` busca con:
- `nombre_completo ILIKE %texto%`
- O `telefono` prefix match (después de normalizar el query).

### REQ-CLI-003
`?modalidad=fijo|consulta|demanda` filtra.

### REQ-CLI-004
`?zona_id=<uuid>` filtra por zona. Si la zona no pertenece a la empresa,
devuelve lista vacía (RLS + filtro explícito).

### REQ-CLI-005
`?activo=true|false` filtra por activo.

### REQ-CLI-006
`GET /api/clientes/{id}` ajeno devuelve 404.

### REQ-CLI-007
`POST /api/clientes` crea (admin), devuelve 201.

### REQ-CLI-008
`POST` con:
- `nombre_completo` vacío → 400 VALIDACION_INPUT.
- `telefono` sin dígitos → 400 VALIDACION_INPUT.

### REQ-CLI-009
`POST` con `zona_id` que no pertenece a la empresa → 422 VALIDACION_SEMANTICA.

### REQ-CLI-010
`telefono` se normaliza al guardar:
- Strip spaces, guiones, paréntesis.
- Si no empieza con `+`, prefija `+54` (default Argentina).
- Ej. `"351 555 1234"` → `"+543515551234"`.

### REQ-CLI-011
`PATCH /api/clientes/{id}` parcial.

### REQ-CLI-012
`DELETE /api/clientes/{id}` soft delete idempotente.

### REQ-CLI-013
Cada POST/PATCH/DELETE genera `EventoDominio` con `entidad_tipo="cliente"`.

## No-requisitos

- Geocoding de `direccion` → coordenadas: TASK-013.
- `lista_precios_id` queda como UUID nullable (la tabla `lista_precios` aparecerá
  en TASK futuro). Si el caller manda un valor, lo persistimos sin validar.
- `ultima_consulta` y `ultima_visita` no se actualizan vía este CRUD — se
  actualizan desde el flujo de campañas (TASK posterior).
- Búsqueda con tildes / sin tildes (collation): MVP usa default. Si en uso real
  aparecen quejas, se agrega `unaccent` o `pg_trgm`.

## Notas de implementación

- Paginación: usar OFFSET/LIMIT simple. Para sets grandes (10k+ clientes)
  considerar keyset pagination en TASK posterior.
- Búsqueda: ILIKE sobre `nombre_completo` + prefix sobre `telefono` con OR.
  Sin índice de texto completo todavía — el filtro `empresa_id` (con índice)
  ya reduce el set drásticamente.
