# Geocoding — REQ-IDs

## Contexto

Convierte `cliente.direccion` (string) en `(lat, lng)` usando Google Maps
Geocoding API. Es best-effort y fail-soft: si falla, el cliente se crea sin
coordenadas.

## Requisitos

### REQ-GEO-001
`infra.geocoding.geocodear(direccion: str) -> tuple[float, float] | None`
devuelve la primera coincidencia o `None`.

### REQ-GEO-002
Sin `GOOGLE_MAPS_API_KEY` configurada, devuelve `None` y no llama a Google.

### REQ-GEO-003
Si Google responde error (status != OK), devuelve `None` y loggea WARNING
con detalle.

### REQ-GEO-004
POST y PATCH `/api/clientes` con `direccion` nueva intentan geocodear y
persisten `coordenadas_lat/lng` si Google responde.

### REQ-GEO-005
Si geocoding falla por cualquier motivo, el cliente se crea/actualiza **sin
coordenadas**. La request HTTP siempre es exitosa.

## No-requisitos

- Reverse geocoding (coordenadas → dirección): no.
- Cache de resultados: no en MVP. Si volume crece, agregar Redis o tabla cache.
- Fallback a otros proveedores (OSM/Nominatim): no.
