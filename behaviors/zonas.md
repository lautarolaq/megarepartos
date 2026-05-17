# Zonas — REQ-IDs

## Contexto

Zonas son agrupaciones geográficas de clientes con día de visita asignado.
El sodero filtra campañas y asigna reparto por zona.

## Requisitos

### REQ-ZONA-001
`GET /api/zonas` devuelve los registros de la empresa, ordenados por `nombre ASC`.

### REQ-ZONA-002
`GET /api/zonas?activo=true` filtra por `activo`.

### REQ-ZONA-003
`GET /api/zonas/{id}` ajeno devuelve 404.

### REQ-ZONA-004
`POST /api/zonas` crea (admin).

### REQ-ZONA-005
`PATCH /api/zonas/{id}` parcial.

### REQ-ZONA-006
`DELETE /api/zonas/{id}` soft delete idempotente.

### REQ-ZONA-007
`dia_visita` debe ser uno de: `lunes | martes | miercoles | jueves | viernes | sabado | domingo`
(o null para zonas sin día asignado). Otros valores devuelven 400 `VALIDACION_INPUT`.

### REQ-ZONA-008
Cada POST/PATCH/DELETE genera `EventoDominio` con `entidad_tipo="zona"`.

## No-requisitos

- Sugerencia automática de particionamiento si una zona crece mucho (sección 6.2)
  es TASK posterior.
- No hay drag-and-drop de clientes entre zonas en este TASK (sección 6.2: TASK UI futuro).
- Soft delete preserva zona aún si tiene clientes asignados — los clientes
  quedan con `zona_id` apuntando a la zona inactiva. La UI los reorganiza después.
