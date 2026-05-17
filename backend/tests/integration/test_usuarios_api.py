"""Tests de integración de `/api/usuarios` (TASK-012 / REQ-USR-001..009)."""

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
from tests.factories import make_empresa, make_usuario
from tests.integration._isolation_helpers import (
    assert_endpoint_isolated_detail_404,
    assert_endpoint_isolated_get,
    assert_endpoint_isolated_mutation_404,
)


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(jwt_secret="test-secret-usr", jwt_algorithm="HS256")


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


async def _seed_admin(db_session: AsyncSession):
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin", nombre="Admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    return empresa, admin


def _token(settings: Settings, *, usuario_id, empresa_id, rol="admin") -> str:
    tok, _ = issue_access_token(
        settings=settings, usuario_id=usuario_id, empresa_id=empresa_id, rol=rol
    )
    return tok


@pytest.mark.integration
@pytest.mark.req("REQ-USR-001")
@pytest.mark.req("REQ-USR-002")
async def test_REQ_USR_001_002_listado_y_filtro_activo(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    await make_usuario(db_session, empresa=empresa, nombre="Beto", rol="operador")
    await make_usuario(db_session, empresa=empresa, nombre="Carla", rol="operador", activo=False)

    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }
    resp = await app_client.get("/api/usuarios", headers=headers)
    assert resp.status_code == 200
    nombres = [u["nombre"] for u in resp.json()["items"]]
    assert nombres == ["Admin", "Beto", "Carla"]

    resp = await app_client.get("/api/usuarios?activo=true", headers=headers)
    nombres_act = {u["nombre"] for u in resp.json()["items"]}
    assert nombres_act == {"Admin", "Beto"}


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-USR-003")
async def test_REQ_USR_003_detalle_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    await assert_endpoint_isolated_detail_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url_template="/api/usuarios/{id}",
        factory=lambda s, e: make_usuario(s, empresa=e, rol="operador"),
    )


@pytest.mark.integration
@pytest.mark.isolation
async def test_listado_usuarios_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009 para `GET /api/usuarios`."""
    await assert_endpoint_isolated_get(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url="/api/usuarios",
        factory=lambda s, e: make_usuario(s, empresa=e, rol="operador"),
        id_extractor=lambda body: {uuid.UUID(u["id"]) for u in body["items"]},
    )


@pytest.mark.integration
@pytest.mark.req("REQ-USR-004")
@pytest.mark.req("REQ-USR-009")
async def test_REQ_USR_004_009_admin_cambia_rol_y_genera_evento(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    from sqlalchemy import select

    from megarepartos.models.evento import EventoDominio

    empresa, admin = await _seed_admin(db_session)
    operador = await make_usuario(db_session, empresa=empresa, rol="operador")
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    resp = await app_client.patch(
        f"/api/usuarios/{operador.id}", headers=headers, json={"rol": "admin"}
    )
    assert resp.status_code == 200
    assert resp.json()["rol"] == "admin"

    # Evento generado.
    evento = (
        await db_session.execute(
            select(EventoDominio).where(EventoDominio.entidad_id == operador.id)
        )
    ).scalar_one()
    assert evento.accion == "modificado"
    assert evento.detalles_jsonb["diff"]["rol"]["a"] == "admin"


@pytest.mark.integration
@pytest.mark.req("REQ-USR-005")
async def test_REQ_USR_005_rol_invalido_400(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    operador = await make_usuario(db_session, empresa=empresa, rol="operador")
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }
    resp = await app_client.patch(
        f"/api/usuarios/{operador.id}", headers=headers, json={"rol": "superuser"}
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.req("REQ-USR-006")
async def test_REQ_USR_006_operador_no_puede_modificar(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    operador = await make_usuario(db_session, empresa=empresa, rol="operador")
    otro = await make_usuario(db_session, empresa=empresa, rol="operador")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=operador.id)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=operador.id, empresa_id=empresa.id, rol='operador')}"
    }

    resp = await app_client.patch(
        f"/api/usuarios/{otro.id}", headers=headers, json={"activo": False}
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.req("REQ-USR-007")
async def test_REQ_USR_007_delete_desactiva(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    operador = await make_usuario(db_session, empresa=empresa, rol="operador")
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }
    resp = await app_client.delete(f"/api/usuarios/{operador.id}", headers=headers)
    assert resp.status_code == 204


@pytest.mark.integration
@pytest.mark.req("REQ-USR-008")
async def test_REQ_USR_008_admin_no_se_auto_desactiva(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    # DELETE sobre uno mismo.
    resp = await app_client.delete(f"/api/usuarios/{admin.id}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICTO_ESTADO"

    # PATCH activo=false sobre uno mismo.
    resp = await app_client.patch(
        f"/api/usuarios/{admin.id}", headers=headers, json={"activo": False}
    )
    assert resp.status_code == 409


@pytest.mark.integration
@pytest.mark.isolation
async def test_REQ_USR_patch_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009: PATCH usuario de empresa ajena → 404."""
    await assert_endpoint_isolated_mutation_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        method="PATCH",
        url_template="/api/usuarios/{id}",
        factory=lambda s, e: make_usuario(s, empresa=e, rol="operador"),
        payload={"activo": False},
    )
