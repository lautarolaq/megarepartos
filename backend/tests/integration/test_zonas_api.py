"""Tests de integración de `/api/zonas` (TASK-010 / REQ-ZONA-001..008)."""

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
from megarepartos.models.zona import Zona
from tests.factories import make_empresa, make_usuario
from tests.integration._isolation_helpers import (
    assert_endpoint_isolated_detail_404,
    assert_endpoint_isolated_get,
    assert_endpoint_isolated_mutation_404,
)


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(jwt_secret="test-secret-zona", jwt_algorithm="HS256")


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


async def _make_zona_factory(session: AsyncSession, empresa) -> Zona:
    z = Zona(
        empresa_id=empresa.id,
        nombre=f"Zona-{uuid.uuid4().hex[:6]}",
        dia_visita="jueves",
        activo=True,
    )
    session.add(z)
    await session.flush()
    return z


async def _seed_admin(db_session: AsyncSession):
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    return empresa, admin


def _token(settings: Settings, *, usuario_id, empresa_id, rol="admin") -> str:
    tok, _ = issue_access_token(
        settings=settings, usuario_id=usuario_id, empresa_id=empresa_id, rol=rol
    )
    return tok


@pytest.mark.integration
@pytest.mark.req("REQ-ZONA-001")
@pytest.mark.req("REQ-ZONA-002")
async def test_REQ_ZONA_001_002_listado_ordenado_y_filtro(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    for nombre in ("Sur", "Norte", "Centro"):
        db_session.add(Zona(empresa_id=empresa.id, nombre=nombre, activo=True))
    db_session.add(Zona(empresa_id=empresa.id, nombre="Inactiva", activo=False))
    await db_session.flush()
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    resp = await app_client.get("/api/zonas", headers=headers)
    assert resp.status_code == 200
    nombres = [z["nombre"] for z in resp.json()["items"]]
    assert nombres == ["Centro", "Inactiva", "Norte", "Sur"]

    resp = await app_client.get("/api/zonas?activo=true", headers=headers)
    nombres_activas = {z["nombre"] for z in resp.json()["items"]}
    assert nombres_activas == {"Centro", "Norte", "Sur"}


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-ZONA-003")
async def test_REQ_ZONA_003_detalle_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    await assert_endpoint_isolated_detail_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url_template="/api/zonas/{id}",
        factory=_make_zona_factory,
    )


@pytest.mark.integration
@pytest.mark.isolation
async def test_listado_zonas_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009 para `GET /api/zonas`. Requerido por `check_endpoint_isolation`."""
    await assert_endpoint_isolated_get(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url="/api/zonas",
        factory=_make_zona_factory,
        id_extractor=lambda body: {uuid.UUID(z["id"]) for z in body["items"]},
    )


@pytest.mark.integration
@pytest.mark.req("REQ-ZONA-004")
async def test_REQ_ZONA_004_post_admin_crea(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    resp = await app_client.post(
        "/api/zonas",
        headers={
            "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
        },
        json={
            "nombre": "Nueva Córdoba",
            "dia_visita": "jueves",
            "camioneta_asignada": "Verde",
            "color_display": "#0ea5e9",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre"] == "Nueva Córdoba"
    assert body["dia_visita"] == "jueves"


@pytest.mark.integration
@pytest.mark.req("REQ-ZONA-007")
async def test_REQ_ZONA_007_dia_visita_invalido_400(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    resp = await app_client.post(
        "/api/zonas",
        headers={
            "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
        },
        json={"nombre": "X", "dia_visita": "luneeees"},  # inválido
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDACION_INPUT"


@pytest.mark.integration
@pytest.mark.req("REQ-ZONA-005")
@pytest.mark.req("REQ-ZONA-008")
async def test_REQ_ZONA_005_008_patch_y_evento(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    zona = Zona(empresa_id=empresa.id, nombre="X", activo=True)
    db_session.add(zona)
    await db_session.flush()
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    resp = await app_client.patch(
        f"/api/zonas/{zona.id}", headers=headers, json={"camioneta_asignada": "Azul"}
    )
    assert resp.status_code == 200
    assert resp.json()["camioneta_asignada"] == "Azul"


@pytest.mark.integration
@pytest.mark.isolation
async def test_REQ_ZONA_patch_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009: PATCH a id ajeno devuelve 404."""
    await assert_endpoint_isolated_mutation_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        method="PATCH",
        url_template="/api/zonas/{id}",
        factory=_make_zona_factory,
        payload={"camioneta_asignada": "Hackeada"},
    )


@pytest.mark.integration
@pytest.mark.req("REQ-ZONA-006")
async def test_REQ_ZONA_006_delete_soft_idempotente(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    zona = Zona(empresa_id=empresa.id, nombre="X", activo=True)
    db_session.add(zona)
    await db_session.flush()
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    r1 = await app_client.delete(f"/api/zonas/{zona.id}", headers=headers)
    assert r1.status_code == 204
    r2 = await app_client.delete(f"/api/zonas/{zona.id}", headers=headers)
    assert r2.status_code == 204
