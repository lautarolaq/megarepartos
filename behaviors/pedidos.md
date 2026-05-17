# Pedidos (vista admin) — REQ-IDs

## Contexto

"Pedidos" no es una tabla propia. Cada respuesta del cliente vía link público
persiste como `evento_dominio` con `accion="respondio_link"` (ver
`behaviors/link_publico.md`). Esta capa expone una vista admin sobre esos
eventos: listado, filtros y stats.

## Requisitos

### REQ-PED-001
`POST /api/publico/c/{token}/respuesta` persiste un `EventoDominio` con
`entidad_tipo="cliente"`, `accion="respondio_link"` y `detalles_jsonb` que
incluye `{accion, productos[], observacion}`. Los nombres de productos se
congelan al momento de la respuesta (no joinea contra `producto` al listar).

### REQ-PED-002
`GET /api/pedidos` (admin) lista respuestas paginadas, orden `fecha DESC`.
Defensa: RLS por `empresa_id` + filtro explícito en la query.

### REQ-PED-003
`GET /api/pedidos` acepta query params opcionales:
- `accion`: `"confirmo"` o `"rechazo"` — filtra por la acción del cliente.
- `desde_dias`: 1..365 — sólo pedidos de los últimos N días (rolling).

### REQ-PED-004
`GET /api/pedidos/stats` (admin) devuelve `{pedidos_hoy, confirmados_hoy,
pedidos_semana, clientes_activos}`. `pedidos_semana` es rolling 7 días.

### REQ-PED-005
`GET /api/pedidos/export.csv` (admin) descarga un CSV con columnas:
Cliente, Teléfono, Acción, Productos (llenos), Envases vacíos a recibir,
Observación, Fecha. Acepta los mismos filtros que el listado (`accion`,
`desde_dias`). Default: `accion=confirmo&desde_dias=7`.

### REQ-PED-006
`GET /api/pedidos/pendientes` (admin) lista clientes con `link_generado`
en los últimos `desde_dias` (default 7) y **sin** `respondio_link`
posterior a ese link. Implementa SPEC 6.9 — para que la sodería pueda
hacer follow-up de los que no respondieron.

`POST /api/clientes/{id}/generar-link` y `POST /api/clientes/generar-links-bulk`
persisten un `evento_dominio` con `accion="link_generado"` para alimentar
esta vista.

## No-requisitos

- No es una tabla `pedido` con CRUD propio.
- No expone borrar/editar respuestas (es auditoría inmutable).
- No filtra por cliente o zona en este sprint (alcanza con buscar el cliente
  desde el listado).
