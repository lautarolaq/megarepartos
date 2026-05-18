"""Tests del router `/api/campanas/*` + endpoint admin `generar-link-broadcast`.

Cubren:
- Listado/detalle aislados por empresa (REQ-MT-009 — cada endpoint nuevo
  necesita su test de isolation, según check_endpoint_isolation).
- Generación de link broadcast persiste un row de Campana con tipo_envio
  broadcast.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.infra.auth import issue_access_token
from megarepartos.infra.db import set_tenant_context
from megarepartos.main import app
from tests.factories import make_campana, make_empresa, make_usuario
from tests.integration._isolation_helpers import (
    assert_endpoint_isolated_detail_404,
    assert_endpoint_isolated_get,
)


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-prod",
        jwt_algorithm="HS256",
        jwt_access_ttl_min=60,
        jwt_refresh_ttl_days=14,
    )


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


# ---- Listado isolation ----


@pytest.mark.integration
@pytest.mark.isolation
async def test_listado_campanas_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """Cubre `GET /api/campanas` para check_endpoint_isolation."""

    async def _factory(s: AsyncSession, e):
        usu = await make_usuario(s, empresa=e)
        return await make_campana(s, empresa=e, usuario=usu)

    await assert_endpoint_isolated_get(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url="/api/campanas",
        factory=_factory,
        id_extractor=lambda body: {uuid.UUID(c["id"]) for c in body["items"]},
    )


# ---- Detalle isolation ----


@pytest.mark.integration
@pytest.mark.isolation
async def test_detalle_campana_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """Cubre `GET /api/campanas/{campana_id}` para check_endpoint_isolation."""

    async def _factory(s: AsyncSession, e):
        usu = await make_usuario(s, empresa=e)
        return await make_campana(s, empresa=e, usuario=usu)

    await assert_endpoint_isolated_detail_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url_template="/api/campanas/{id}",
        factory=_factory,
    )


# ---- generar-link-broadcast persiste campana ----


@pytest.mark.integration
async def test_generar_link_broadcast_crea_campana(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """`POST /api/clientes/generar-link-broadcast` debe crear una Campana con
    tipo_envio=broadcast y devolver `campana_id` en la respuesta.
    """
    from sqlalchemy import text

    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    await db_session.commit()

    access, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol=admin.rol
    )

    resp = await app_client.post(
        "/api/clientes/generar-link-broadcast",
        headers={"Authorization": f"Bearer {access}"},
        json={"nombre": "Test campana", "mensaje": "Hola {link}", "zona_id": None},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["campana_id"]
    assert body["url"].startswith("http")
    assert "/b/" in body["url"]

    # Verificar que la Campana fue persistida con tipo_envio=broadcast.
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    row = (
        await db_session.execute(
            text(
                "SELECT destinatarios_origen->>'tipo_envio' AS t, nombre "
                "FROM campana WHERE id = :id"
            ),
            {"id": uuid.UUID(body["campana_id"])},
        )
    ).one_or_none()
    assert row is not None
    # row es una named tuple — los campos seleccionados son `t` y `nombre`
    assert row[0] == "broadcast"
    assert row[1] == "Test campana"


# isolation del endpoint admin /api/clientes/generar-link-broadcast
# (no necesita el helper get porque es un POST que crea recursos — un test que
# tokena con otra empresa y verifica que la campana queda en la empresa correcta)
@pytest.mark.integration
@pytest.mark.isolation
async def test_generar_link_broadcast_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """Cubre `POST /api/clientes/generar-link-broadcast` para check_endpoint_isolation.
    Verifica que la campaña creada queda asociada a la empresa del admin,
    no a otra.
    """
    from sqlalchemy import text

    empresa_a = await make_empresa(db_session)
    admin_a = await make_usuario(db_session, empresa=empresa_a, rol="admin")
    empresa_b = await make_empresa(db_session)
    await make_usuario(db_session, empresa=empresa_b, rol="admin")
    await db_session.commit()

    access_a, _ = issue_access_token(
        settings=settings,
        usuario_id=admin_a.id,
        empresa_id=empresa_a.id,
        rol=admin_a.rol,
    )

    resp = await app_client.post(
        "/api/clientes/generar-link-broadcast",
        headers={"Authorization": f"Bearer {access_a}"},
        json={"nombre": "Aislamiento", "mensaje": "x", "zona_id": None},
    )
    assert resp.status_code == 200
    campana_id = resp.json()["campana_id"]

    # Verificar que la campana_id pertenece a empresa A, no B.
    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=admin_a.id)
    row = (
        await db_session.execute(
            text("SELECT empresa_id FROM campana WHERE id = :id"),
            {"id": uuid.UUID(campana_id)},
        )
    ).scalar_one()
    assert row == empresa_a.id
    assert row != empresa_b.id
