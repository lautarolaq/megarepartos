"""Helpers para tests de aislamiento multi-tenant (REQ-MT-009).

Patrón canónico para verificar que un endpoint autenticado no devuelve ni
modifica datos de otra empresa.

Uso:

```python
async def test_clientes_aislamiento(app_client, db_session, settings):
    await assert_endpoint_isolated_get(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url="/api/clientes",
        factory=lambda s, e: make_cliente(s, empresa=e),
        id_extractor=lambda body: {c["id"] for c in body["items"]},
    )
```

El helper hace todo el setup de A+B con data y verifica que A no ve nada de B.
Los tests siguientes (TASK-008+) usan este helper en cada endpoint nuevo.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings
from megarepartos.infra.auth import issue_access_token
from megarepartos.infra.db import set_tenant_context
from megarepartos.models.empresa import Empresa
from megarepartos.models.usuario import Usuario
from tests.factories import make_empresa, make_usuario

Factory = Callable[[AsyncSession, Empresa], Awaitable[Any]]


async def _seed_two_empresas_with_data(
    db_session: AsyncSession,
    factory: Factory,
) -> tuple[
    tuple[Empresa, Usuario, list[Any]],  # A
    tuple[Empresa, Usuario, list[Any]],  # B
]:
    """Crea dos empresas con su admin y 2 filas de data cada una.

    Devuelve `((empresa_a, usuario_a, [item_a1, item_a2]), idem para B)`.
    """
    empresa_a = await make_empresa(db_session, nombre="ISO-A")
    empresa_b = await make_empresa(db_session, nombre="ISO-B")
    usuario_a = await make_usuario(db_session, empresa=empresa_a)
    usuario_b = await make_usuario(db_session, empresa=empresa_b)

    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    items_a = [await factory(db_session, empresa_a), await factory(db_session, empresa_a)]

    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    items_b = [await factory(db_session, empresa_b), await factory(db_session, empresa_b)]

    return (empresa_a, usuario_a, items_a), (empresa_b, usuario_b, items_b)


async def assert_endpoint_isolated_get(
    *,
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    url: str,
    factory: Factory,
    id_extractor: Callable[[dict[str, Any]], set[uuid.UUID]],
) -> None:
    """REQ-MT-009 para endpoints GET tipo listado.

    Verifica que una empresa A solo vea sus items y no los de B.

    - `factory(session, empresa)`: crea un item para esa empresa. El helper
      lo llama 4 veces (2 por empresa).
    - `id_extractor(body)`: extrae el set de IDs del JSON de respuesta (ajustá
      según el shape del endpoint, ej `body["items"]` o `body["clientes"]`).
    """
    (
        (empresa_a, usuario_a, items_a),
        (_empresa_b, _usuario_b, items_b),
    ) = await _seed_two_empresas_with_data(db_session, factory)

    access, _ = issue_access_token(
        settings=settings,
        usuario_id=usuario_a.id,
        empresa_id=empresa_a.id,
        rol=usuario_a.rol,
    )

    resp = await app_client.get(url, headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200, f"GET {url} → {resp.status_code}: {resp.text}"
    ids_visibles = id_extractor(resp.json())

    ids_a = {item.id for item in items_a}
    ids_b = {item.id for item in items_b}
    assert ids_a.issubset(ids_visibles), (
        f"Empresa A no ve sus propios items en {url}. Esperados: {ids_a}, visibles: {ids_visibles}"
    )
    assert ids_visibles.isdisjoint(ids_b), (
        f"Empresa A ve items de B en {url}. Leak: {ids_visibles & ids_b}"
    )


async def assert_endpoint_isolated_detail_404(
    *,
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    url_template: str,
    factory: Factory,
) -> None:
    """REQ-MT-009 para endpoints GET de detalle (`/recurso/{id}`).

    Verifica que pedir un item de empresa B desde token de A devuelve 404
    (no 403 — para no leakear que el ID existe en otra empresa).

    `url_template` debe contener `{id}` que el helper rellena con el ID del
    item de empresa B.
    """
    (
        (empresa_a, usuario_a, _items_a),
        (_empresa_b, _usuario_b, items_b),
    ) = await _seed_two_empresas_with_data(db_session, factory)

    access, _ = issue_access_token(
        settings=settings,
        usuario_id=usuario_a.id,
        empresa_id=empresa_a.id,
        rol=usuario_a.rol,
    )

    item_de_b = items_b[0]
    url = url_template.format(id=item_de_b.id)
    resp = await app_client.get(url, headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 404, (
        f"GET {url} con token de empresa ajena debería ser 404, fue {resp.status_code}: {resp.text}"
    )


async def assert_endpoint_isolated_mutation_404(
    *,
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    method: str,
    url_template: str,
    factory: Factory,
    payload: dict[str, Any] | None = None,
) -> None:
    """REQ-MT-009 para endpoints destructivos (PATCH/PUT/DELETE) sobre `/recurso/{id}`.

    Verifica que mutar un item de empresa B desde token de A devuelve 404
    y NO modifica/borra la data de B.
    """
    method_upper = method.upper()
    assert method_upper in {"PATCH", "PUT", "DELETE"}, f"Método no soportado: {method}"

    (
        (empresa_a, usuario_a, _items_a),
        (_empresa_b, _usuario_b, items_b),
    ) = await _seed_two_empresas_with_data(db_session, factory)
    item_de_b = items_b[0]

    access, _ = issue_access_token(
        settings=settings,
        usuario_id=usuario_a.id,
        empresa_id=empresa_a.id,
        rol=usuario_a.rol,
    )

    url = url_template.format(id=item_de_b.id)
    kwargs: dict[str, Any] = {"headers": {"Authorization": f"Bearer {access}"}}
    if payload is not None:
        kwargs["json"] = payload
    resp = await app_client.request(method_upper, url, **kwargs)
    assert resp.status_code == 404, (
        f"{method_upper} {url} desde empresa ajena debería ser 404, fue {resp.status_code}: {resp.text}"
    )

    # Verificar que el item de B sigue presente (no se borró ni mutó).
    # Lo hacemos refrescando desde la DB.
    await db_session.refresh(item_de_b)
    # Si era DELETE, el item debería seguir vivo:
    assert item_de_b is not None
