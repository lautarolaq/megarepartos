# Envases — REQ-IDs

## Contexto

Los envases retornables son los recipientes asociados a productos retornables.
Cada empresa tiene su catálogo. Solo admin gestiona.

## Requisitos

### REQ-ENV-001
`GET /api/envases` devuelve `{items: [...]}` con los envases de la empresa
del JWT, ordenados por `nombre ASC`.

### REQ-ENV-002
`GET /api/envases?activo=true` filtra por `activo`.

### REQ-ENV-003
`GET /api/envases/{id}` ajeno devuelve 404 `RECURSO_NO_ENCONTRADO`.

### REQ-ENV-004
`POST /api/envases` crea (admin), devuelve 201.

### REQ-ENV-005
`PATCH /api/envases/{id}` parcial.

### REQ-ENV-006
`DELETE /api/envases/{id}` soft delete idempotente.

### REQ-ENV-007
`POST` como operador devuelve 403 `PERMISO_DENEGADO`.

### REQ-ENV-008
Cada escritura genera `EventoDominio` con `entidad_tipo="envase"`.

## No-requisitos

- No bloquear borrado de envases referenciados por productos activos en este
  TASK. Si el admin borra un envase usado, los productos quedan con
  `envase_id` apuntando a NULL (FK `ON DELETE SET NULL`).
- No hay endpoint para reactivar — se hace via PATCH `{activo: true}`.
