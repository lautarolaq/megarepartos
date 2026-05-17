"""Tests de integración de `/api/envases` (TASK-009 / REQ-ENV-001..008)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.infra.auth import issue_access_token
from megarepartos.infra.db import set_tenant_context
from megarepartos.main import app
from megarepartos.models.evento import EventoDominio
from megarepartos.models.producto import Envase
from tests.factories import make_empresa, make_usuario
from tests.integration._isolation_helpers import (
    assert_endpoint_isolated_detail_404,
    assert_endpoint_isolated_get,
    assert_endpoint_isolated_mutation_404,
)


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(jwt_secret="test-secret-env", jwt_algorithm="HS256")


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


async def _make_envase_factory(session: AsyncSession, empresa) -> Envase:
    """Factory para tests de aislamiento."""
    e = Envase(
        empresa_id=empresa.id,
        nombre=f"Env-{uuid.uuid4().hex[:6]}",
        activo=True,
    )
    session.add(e)
    await session.flush()
    return e


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


# ---- REQ-ENV-001 / 003 + isolation ----


@pytest.mark.integration
@pytest.mark.req("REQ-ENV-001")
@pytest.mark.req("REQ-ENV-002")
async def test_REQ_ENV_001_002_listado_ordenado_y_filtro(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    for nombre in ("Z", "A", "M"):
        db_session.add(Envase(empresa_id=empresa.id, nombre=nombre, activo=True))
    db_session.add(Envase(empresa_id=empresa.id, nombre="X-inactivo", activo=False))
    await db_session.flush()
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    # Sin filtro: todos (incluye inactivo), ordenados por nombre.
    resp = await app_client.get("/api/envases", headers=headers)
    assert resp.status_code == 200
    nombres = [e["nombre"] for e in resp.json()["items"]]
    assert nombres == ["A", "M", "X-inactivo", "Z"]

    # activo=true: solo los 3 activos.
    resp = await app_client.get("/api/envases?activo=true", headers=headers)
    nombres_activos = {e["nombre"] for e in resp.json()["items"]}
    assert nombres_activos == {"A", "M", "Z"}


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-ENV-003")
async def test_REQ_ENV_003_detalle_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    await assert_endpoint_isolated_detail_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url_template="/api/envases/{id}",
        factory=_make_envase_factory,
    )


@pytest.mark.integration
@pytest.mark.isolation
async def test_listado_envases_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009 para `GET /api/envases`. Requerido por `check_endpoint_isolation`."""
    await assert_endpoint_isolated_get(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url="/api/envases",
        factory=_make_envase_factory,
        id_extractor=lambda body: {uuid.UUID(e["id"]) for e in body["items"]},
    )


# ---- REQ-ENV-004 + 007 ----


@pytest.mark.integration
@pytest.mark.req("REQ-ENV-004")
async def test_REQ_ENV_004_post_admin_crea(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    resp = await app_client.post(
        "/api/envases",
        headers={
            "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
        },
        json={"nombre": "Botellón 20L", "valor_referencial": "8000.00"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre"] == "Botellón 20L"
    assert body["valor_referencial"] == "8000.00"


@pytest.mark.integration
@pytest.mark.req("REQ-ENV-007")
async def test_REQ_ENV_007_post_operador_403(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    operador = await make_usuario(db_session, empresa=empresa, rol="operador")
    resp = await app_client.post(
        "/api/envases",
        headers={
            "Authorization": f"Bearer {_token(settings, usuario_id=operador.id, empresa_id=empresa.id, rol='operador')}"
        },
        json={"nombre": "X"},
    )
    assert resp.status_code == 403


# ---- REQ-ENV-005 / 008 ----


@pytest.mark.integration
@pytest.mark.req("REQ-ENV-005")
@pytest.mark.req("REQ-ENV-008")
async def test_REQ_ENV_005_008_patch_y_eventos(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    envase = Envase(empresa_id=empresa.id, nombre="Original", activo=True)
    db_session.add(envase)
    await db_session.flush()
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    resp = await app_client.patch(
        f"/api/envases/{envase.id}", headers=headers, json={"nombre": "Renombrado"}
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Renombrado"

    # Evento de modificación generado.
    evento = (
        await db_session.execute(select(EventoDominio).where(EventoDominio.entidad_id == envase.id))
    ).scalar_one()
    assert evento.accion == "modificado"


@pytest.mark.integration
@pytest.mark.isolation
async def test_REQ_ENV_patch_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009: PATCH a id de empresa B desde token A devuelve 404."""
    await assert_endpoint_isolated_mutation_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        method="PATCH",
        url_template="/api/envases/{id}",
        factory=_make_envase_factory,
        payload={"nombre": "Hackeado"},
    )


# ---- REQ-ENV-006 ----


@pytest.mark.integration
@pytest.mark.req("REQ-ENV-006")
async def test_REQ_ENV_006_delete_soft_idempotente(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    envase = Envase(empresa_id=empresa.id, nombre="X", activo=True)
    db_session.add(envase)
    await db_session.flush()
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    r1 = await app_client.delete(f"/api/envases/{envase.id}", headers=headers)
    assert r1.status_code == 204
    r2 = await app_client.delete(f"/api/envases/{envase.id}", headers=headers)
    assert r2.status_code == 204
