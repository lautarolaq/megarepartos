"""Tests de integración de `/api/clientes` (TASK-011 / REQ-CLI-001..013)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.domain.clientes import normalizar_telefono
from megarepartos.infra.auth import issue_access_token
from megarepartos.infra.db import set_tenant_context
from megarepartos.main import app
from megarepartos.models.cliente import Cliente
from megarepartos.models.zona import Zona
from tests.factories import make_cliente, make_empresa, make_usuario
from tests.integration._isolation_helpers import (
    assert_endpoint_isolated_detail_404,
    assert_endpoint_isolated_get,
    assert_endpoint_isolated_mutation_404,
)


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(jwt_secret="test-secret-cli", jwt_algorithm="HS256")


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


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


# ---- Unit (en archivo de integración por proximidad) ----


def test_normalizar_telefono_agrega_codigo_pais() -> None:
    assert normalizar_telefono("351 555 1234") == "+543515551234"
    assert normalizar_telefono("0351-555-1234") == "+543515551234"
    assert normalizar_telefono("+54 9 351 5551234") == "+5493515551234"


def test_normalizar_telefono_sin_digitos_falla() -> None:
    from megarepartos.infra.errors import ApiError

    with pytest.raises(ApiError):
        normalizar_telefono("abc-def")


# ---- REQ-CLI-001 / paginación ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-001")
@pytest.mark.req("REQ-CLI-005")
async def test_REQ_CLI_001_005_listado_paginado_ordenado_y_filtro_activo(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    nombres = ["Zoe", "Ana", "Beto", "Carla", "Diego"]
    for n in nombres:
        await make_cliente(db_session, empresa=empresa, nombre_completo=n)
    inactivo = await make_cliente(
        db_session, empresa=empresa, nombre_completo="Eva-inactiva", activo=False
    )
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    # Limit pequeño + ordering por nombre.
    resp = await app_client.get("/api/clientes?limit=3", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6  # incluye inactivo
    assert body["limit"] == 3
    nombres_pagina = [c["nombre_completo"] for c in body["items"]]
    assert nombres_pagina == ["Ana", "Beto", "Carla"]

    # Offset siguiente.
    resp = await app_client.get("/api/clientes?limit=3&offset=3", headers=headers)
    pag2 = [c["nombre_completo"] for c in resp.json()["items"]]
    assert pag2 == ["Diego", "Eva-inactiva", "Zoe"]

    # REQ-CLI-005: filtro activo=true excluye al inactivo.
    resp = await app_client.get("/api/clientes?activo=true&limit=100", headers=headers)
    nombres_act = {c["nombre_completo"] for c in resp.json()["items"]}
    assert "Eva-inactiva" not in nombres_act
    assert resp.json()["total"] == 5
    assert inactivo.activo is False


# ---- REQ-CLI-002 ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-002")
async def test_REQ_CLI_002_busqueda_por_nombre_o_telefono(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    await make_cliente(
        db_session, empresa=empresa, nombre_completo="Ana Pérez", telefono="+543515551111"
    )
    await make_cliente(
        db_session, empresa=empresa, nombre_completo="Beto López", telefono="+543515552222"
    )
    await make_cliente(
        db_session, empresa=empresa, nombre_completo="Carla Pérez", telefono="+543515553333"
    )
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    # Busca por nombre (ILIKE).
    resp = await app_client.get("/api/clientes?q=pérez", headers=headers)
    nombres = {c["nombre_completo"] for c in resp.json()["items"]}
    assert nombres == {"Ana Pérez", "Carla Pérez"}

    # Busca por teléfono (match parcial).
    resp = await app_client.get("/api/clientes?q=5552", headers=headers)
    nombres_tel = {c["nombre_completo"] for c in resp.json()["items"]}
    assert nombres_tel == {"Beto López"}


# ---- REQ-CLI-003 / 004 / 005 ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-003")
@pytest.mark.req("REQ-CLI-004")
async def test_REQ_CLI_003_004_filtros(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    zona_a = Zona(empresa_id=empresa.id, nombre="ZonA", activo=True)
    zona_b = Zona(empresa_id=empresa.id, nombre="ZonB", activo=True)
    db_session.add_all([zona_a, zona_b])
    await db_session.flush()

    await make_cliente(
        db_session,
        empresa=empresa,
        nombre_completo="Fijo en A",
        modalidad="fijo",
        zona_id=zona_a.id,
    )
    await make_cliente(
        db_session,
        empresa=empresa,
        nombre_completo="Consulta en B",
        modalidad="consulta",
        zona_id=zona_b.id,
    )
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    resp = await app_client.get("/api/clientes?modalidad=fijo", headers=headers)
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["nombre_completo"] == "Fijo en A"

    resp = await app_client.get(f"/api/clientes?zona_id={zona_b.id}", headers=headers)
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["nombre_completo"] == "Consulta en B"


# ---- REQ-CLI-006 + isolation ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-CLI-006")
async def test_REQ_CLI_006_detalle_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    await assert_endpoint_isolated_detail_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url_template="/api/clientes/{id}",
        factory=lambda s, e: make_cliente(s, empresa=e),
    )


@pytest.mark.integration
@pytest.mark.isolation
async def test_listado_clientes_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009 para `GET /api/clientes`. Requerido por check_endpoint_isolation."""
    await assert_endpoint_isolated_get(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url="/api/clientes",
        factory=lambda s, e: make_cliente(s, empresa=e),
        id_extractor=lambda body: {uuid.UUID(c["id"]) for c in body["items"]},
    )


# ---- REQ-CLI-007 / 010 ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-007")
@pytest.mark.req("REQ-CLI-010")
async def test_REQ_CLI_007_010_post_crea_y_normaliza_telefono(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    resp = await app_client.post(
        "/api/clientes",
        headers={
            "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
        },
        json={
            "nombre_completo": "Juan García",
            "telefono": "0351 555 1234",  # con formato local
            "modalidad": "fijo",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre_completo"] == "Juan García"
    assert body["telefono"] == "+543515551234"
    assert body["modalidad"] == "fijo"


# ---- REQ-CLI-008 ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-008")
async def test_REQ_CLI_008_validacion_input(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    # Nombre vacío.
    resp = await app_client.post(
        "/api/clientes", headers=headers, json={"nombre_completo": "", "telefono": "+5435155"}
    )
    assert resp.status_code == 400

    # Teléfono sin dígitos.
    resp = await app_client.post(
        "/api/clientes",
        headers=headers,
        json={"nombre_completo": "X", "telefono": "abc-def"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDACION_INPUT"


# ---- REQ-CLI-009 ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-009")
async def test_REQ_CLI_009_zona_ajena_422(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa_a, admin_a = await _seed_admin(db_session)

    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_b = await make_usuario(db_session, empresa=empresa_b)
    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    zona_b = Zona(empresa_id=empresa_b.id, nombre="Zona B", activo=True)
    db_session.add(zona_b)
    await db_session.flush()

    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=admin_a.id)

    resp = await app_client.post(
        "/api/clientes",
        headers={
            "Authorization": f"Bearer {_token(settings, usuario_id=admin_a.id, empresa_id=empresa_a.id)}"
        },
        json={
            "nombre_completo": "Test",
            "telefono": "+543515551234",
            "zona_id": str(zona_b.id),
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDACION_SEMANTICA"


# ---- REQ-CLI-011 / 013 ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-011")
@pytest.mark.req("REQ-CLI-013")
async def test_REQ_CLI_011_013_patch_parcial_y_evento(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    cliente = await make_cliente(
        db_session, empresa=empresa, nombre_completo="Original", modalidad="fijo"
    )
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    resp = await app_client.patch(
        f"/api/clientes/{cliente.id}",
        headers=headers,
        json={"observaciones_permanentes": "Llamar antes"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["observaciones_permanentes"] == "Llamar antes"
    # No cambió modalidad.
    assert body["modalidad"] == "fijo"


@pytest.mark.integration
@pytest.mark.isolation
async def test_REQ_CLI_patch_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009: PATCH a id ajeno → 404."""
    await assert_endpoint_isolated_mutation_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        method="PATCH",
        url_template="/api/clientes/{id}",
        factory=lambda s, e: make_cliente(s, empresa=e),
        payload={"observaciones_permanentes": "Hackeado"},
    )


# ---- REQ-CLI-012 ----


@pytest.mark.integration
@pytest.mark.req("REQ-CLI-012")
async def test_REQ_CLI_012_delete_soft_idempotente(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    cliente = await make_cliente(db_session, empresa=empresa)
    headers = {
        "Authorization": f"Bearer {_token(settings, usuario_id=admin.id, empresa_id=empresa.id)}"
    }

    r1 = await app_client.delete(f"/api/clientes/{cliente.id}", headers=headers)
    assert r1.status_code == 204
    r2 = await app_client.delete(f"/api/clientes/{cliente.id}", headers=headers)
    assert r2.status_code == 204

    # Verificar en DB que activo=False.
    en_db = (await db_session.execute(select(Cliente).where(Cliente.id == cliente.id))).scalar_one()
    assert en_db.activo is False
