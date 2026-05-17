# Multi-tenant + Row-Level Security — REQ-IDs

## Contexto

Megarepartos aloja N empresas. El **invariante #1** del producto es: una
empresa no puede ver/modificar datos de otra. Lo enforcemos con tres capas:

1. **JWT con `empresa_id`** (TASK-001): la identidad de cada request está
   firmada por nosotros.
2. **Repositorios con `empresa_id` automático** (TASK-004, futuro): toda
   query del código de aplicación filtra por `empresa_id` del usuario logueado.
3. **Row-Level Security de Postgres** (esta tarea): aún si el código olvida
   filtrar, la DB rechaza. La defensa más profunda.

Cada request autenticada setea `SET LOCAL app.empresa_id = '<uuid>'` en su
conexión Postgres. Las policies usan eso para filtrar.

## Requisitos

### REQ-MT-001

Todas las tablas de negocio tienen RLS habilitado **y forzado** (`FORCE ROW
LEVEL SECURITY`) — incluso el owner del schema respeta las policies:

- Directas (tienen columna `empresa_id`): `cliente`, `producto`, `envase`,
  `zona`, `campana`, `template_mensaje`, `template_formulario`,
  `evento_dominio`, `token_extension`, `sheet_referencia`.
- Indirectas (heredan `empresa_id` vía FK): `producto_habitual` (→ cliente),
  `mensaje_enviado` (→ campana), `respuesta_link` (→ mensaje_enviado),
  `confirmacion_pedido` (→ cliente).

NO tienen RLS habilitado (acceso controlado por otros mecanismos):
- `empresa`, `usuario`: accedidas por el auth flow.
- `plan`: config compartida del sistema.

### REQ-MT-002

La dep `authenticated_session` (FastAPI) hace:

```sql
SELECT set_config('app.empresa_id', '<uuid>', true);
SELECT set_config('app.usuario_id', '<uuid>', true);
```

con `is_local=true` (equivale a `SET LOCAL`) antes de yieldear la session.
Los routers que necesitan datos de negocio dependen de `authenticated_session`
en vez de `get_session`.

### REQ-MT-003

Dadas dos empresas A y B con clientes, un `SELECT * FROM cliente` ejecutado
en una connection con `app.empresa_id` = A solo devuelve clientes de A.

### REQ-MT-004

Un `INSERT INTO cliente (empresa_id, ...) VALUES (<id de B>, ...)` ejecutado
desde contexto A falla con violación de policy `WITH CHECK`.

### REQ-MT-005

Un `UPDATE cliente SET ... WHERE id = <de B>` desde contexto A afecta 0 rows.
Lo mismo `DELETE`. La policy oculta el row, no levanta error — esto evita
que un atacante enumere IDs por mensaje de error.

### REQ-MT-006

Si `app.empresa_id` no está seteado (string vacío al hacer
`current_setting('app.empresa_id', true)`), las queries devuelven 0 rows.
Fail-closed: el código que olvida pasar por `authenticated_session` no ve
datos.

### REQ-MT-007

Los registros preset de `template_mensaje` y `template_formulario` tienen
`empresa_id IS NULL` y son visibles desde **cualquier** empresa. La policy
usa `empresa_id IS NULL OR empresa_id::text = current_setting(...)`.

### REQ-MT-008

Las tablas indirectas (sin columna `empresa_id` propia) tienen policies con
`EXISTS` sobre el padre. Ejemplo `producto_habitual`:

```sql
USING (
  EXISTS (
    SELECT 1 FROM cliente c
    WHERE c.id = producto_habitual.cliente_id
      AND c.empresa_id::text = current_setting('app.empresa_id', true)
  )
)
```

Esto recursivamente respeta la cadena (el SELECT interno también pasa por
RLS de cliente).

### REQ-MT-009

`assert_endpoint_isolated(app_client, *, method, url, factory, ...)` (helper
en `tests/integration/_isolation_helpers.py`) implementa el patrón estándar
de test de aislamiento para un endpoint cualquiera:

1. Crea empresa A + usuario admin A + data via `factory(session, empresa_a)`.
2. Crea empresa B + usuario admin B + data via `factory(session, empresa_b)`.
3. Emite access token para usuario A.
4. Hace la request con ese token a `url`.
5. Verifica que en la respuesta solo aparecen IDs de data de A (no de B).
6. Si el método es destructivo (PATCH/PUT/DELETE) sobre un ID de B, verifica
   que devuelve 404 y que la data de B sigue intacta.

Reemplaza ~30 líneas de boilerplate por una llamada de una línea.

### REQ-MT-010

Property-based test (con `hypothesis`) sobre `cliente`:

- Genera N empresas (2..5) cada una con M clientes (0..10).
- Para cada empresa, hace `set_tenant_context` y `SELECT * FROM cliente`.
- Invariante: la cardinalidad y el conjunto de IDs devueltos coincide
  **exactamente** con los clientes creados para esa empresa.

### REQ-MT-011

`scripts/check_endpoint_isolation.py` parsea los routers en
`backend/src/megarepartos/api/*.py` y lista los endpoints que dependen de
`authenticated_session`. Para cada uno verifica que exista al menos un test
con `@pytest.mark.isolation` que mencione el path (o un alias documentado).

Los endpoints `/api/auth/*` no requieren test de aislamiento (son pre-tenant).
La lista de exenciones está hardcoded en el script.

### REQ-MT-012

El check se ejecuta en el job `behavior-coverage` de CI (`ci.yml`). Falla el
build si encuentra endpoints autenticados sin test de aislamiento.

## No-requisitos

- No hay bypass aplicación-level. Los pocos lugares que necesitan operar
  sobre múltiples empresas (jobs nocturnos, admin interno) corren bajo un
  rol Postgres distinto que tiene `BYPASSRLS`.
- Performance: las policies sobre tablas indirectas usan EXISTS, lo que
  agrega un seek por query. Con índice en `cliente.empresa_id` (ya creado),
  el costo es bajo. Si aparece como bottleneck, se denormaliza `empresa_id`
  a las tablas indirectas en un TASK futuro.

## Notas de implementación

- `FORCE ROW LEVEL SECURITY` es necesario porque la migración corre como
  superuser y la app usa el mismo rol (no separamos roles en MVP).
- Cuando se separe el rol de migración del rol de app (post-MVP), se puede
  quitar `FORCE` y dar `BYPASSRLS` solo al rol de migración.
- Los tests usan `set_tenant_context(session, empresa_id, usuario_id)` para
  emular lo que hace `authenticated_session` sin pasar por HTTP.
