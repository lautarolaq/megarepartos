# Roles + permisos — REQ-IDs

## Contexto

Dos roles en MVP (sección 9.2 del SPEC):

- **Admin**: catálogo, clientes, usuarios, suscripción, todo.
- **Operador**: campañas + visualización. No toca catálogo, no borra
  campañas pasadas, no gestiona usuarios.

`require_rol(*permitidos)` en `infra/auth.py` es el dep que los endpoints
usan para enforcear permisos.

## Requisitos

### REQ-ROL-001

`require_rol("admin")` permite pasar la request si los claims del JWT tienen
`rol == "admin"`. No hace nada extra (no toca DB), solo valida claims.

### REQ-ROL-002

`require_rol("admin")` levanta `ApiError(PERMISO_DENEGADO)` (HTTP 403) si
el usuario es `operador`. El mensaje genérico:
`"No tenés permiso para esta acción."`

### REQ-ROL-003

`require_rol("admin", "operador")` acepta cualquiera de los dos. Para
endpoints accesibles a ambos roles (ej. crear campaña).

### REQ-ROL-004

El mensaje del 403 NO incluye la lista de roles válidos. No leakeamos
información sobre la superficie de permisos (un atacante no puede enumerar
qué endpoints requieren qué rol).

### REQ-ROL-005

`require_rol` se compone con `authenticated_session`. La cadena típica:

```python
@router.delete("/productos/{id}")
async def delete_producto(
    _admin: Annotated[TokenClaims, Depends(require_rol("admin"))],
    session: Annotated[AsyncSession, Depends(authenticated_session)],
    ...
): ...
```

`require_rol` retorna los claims (igual que `current_claims`) para que el
caller pueda accederlos si los necesita.

## No-requisitos

- No hay "permission bits" granulares (read/write/delete por entidad).
  MVP usa roles simples.
- No validamos rol contra DB. El JWT es la fuente de verdad — si el rol
  del usuario cambia, su access token sigue siendo válido hasta expirar
  (max 60min). Para revocación inmediata, el admin desactiva al usuario
  (`activo=false`) — la próxima request falla en `obtener_contexto_actual`.

## Notas de implementación

- `require_rol` es una factory: devuelve una función que FastAPI puede
  usar como dep. Ejemplo: `Depends(require_rol("admin"))`.
- Si en el futuro hay roles jerárquicos (admin > supervisor > operador),
  se agrega una tabla de jerarquía sin cambiar la firma de `require_rol`.
