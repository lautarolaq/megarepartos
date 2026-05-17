"""Tests de `/api/empresa/me`."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.infra.auth import issue_access_token
from megarepartos.infra.db import set_tenant_context
from megarepartos.main import app
from tests.factories import make_empresa, make_usuario


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(jwt_secret="test-secret-empresa", jwt_algorithm="HS256")


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


def _token(settings: Settings, *, usuario_id, empresa_id, rol="admin") -> str:
    tok, _ = issue_access_token(
        settings=settings, usuario_id=usuario_id, empresa_id=empresa_id, rol=rol
    )
    return tok


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-008")
async def test_get_empresa_me(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session, nombre="Sodería X")
    usuario = await make_usuario(db_session, empresa=empresa)
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=usuario.id)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=usuario.id, empresa_id=empresa.id)}"
    }
    resp = await app_client.get("/api/empresa/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["nombre"] == "Sodería X"
    assert "estado_suscripcion" in body


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-007")
async def test_patch_empresa_me_admin(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session, nombre="Vieja")
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }
    resp = await app_client.patch(
        "/api/empresa/me",
        headers=headers,
        json={"nombre": "Sodería Nueva", "direccion_deposito": "Av. Colón 123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nombre"] == "Sodería Nueva"
    assert body["direccion_deposito"] == "Av. Colón 123"


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-009")
async def test_patch_mensaje_default_link(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """El mensaje_default_link se guarda en config_jsonb y vuelve en el GET."""
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    msg = "Hola {nombre}! Confirmá tu pedido: {link}"
    r1 = await app_client.patch(
        "/api/empresa/me", headers=headers, json={"mensaje_default_link": msg}
    )
    assert r1.status_code == 200
    assert r1.json()["mensaje_default_link"] == msg

    # GET refleja el cambio.
    r2 = await app_client.get("/api/empresa/me", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["mensaje_default_link"] == msg

    # Setear a None lo borra.
    r3 = await app_client.patch(
        "/api/empresa/me", headers=headers, json={"mensaje_default_link": None}
    )
    assert r3.status_code == 200
    assert r3.json()["mensaje_default_link"] is None


@pytest.mark.integration
async def test_patch_empresa_me_no_admin_403(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    operador = await make_usuario(db_session, empresa=empresa, rol="operador")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=operador.id)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=operador.id, empresa_id=empresa.id, rol='operador')}"
    }
    resp = await app_client.patch("/api/empresa/me", headers=headers, json={"nombre": "Hack"})
    assert resp.status_code == 403
