"""Tests del listado de pedidos (/api/pedidos) — admin view sobre evento_dominio."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.infra.auth import issue_access_token, sign_link_token
from megarepartos.infra.db import set_tenant_context
from megarepartos.main import app
from tests.factories import make_cliente, make_empresa, make_usuario


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(jwt_secret="test-secret-pedidos", jwt_algorithm="HS256")


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-PED-001")
@pytest.mark.req("REQ-PED-002")
async def test_listar_pedidos_filtra_por_empresa(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """Crear respuestas para 2 clientes de empresa A y 1 de B. El admin de A
    sólo ve los suyos. Defensa en profundidad: RLS + filtro explícito.
    """
    empresa_a = await make_empresa(db_session, nombre="A")
    admin_a = await make_usuario(db_session, empresa=empresa_a, rol="admin")
    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_b = await make_usuario(db_session, empresa=empresa_b)

    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=admin_a.id)
    cliente_a1 = await make_cliente(db_session, empresa=empresa_a, nombre_completo="Cliente A1")
    cliente_a2 = await make_cliente(db_session, empresa=empresa_a, nombre_completo="Cliente A2")

    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    cliente_b1 = await make_cliente(db_session, empresa=empresa_b, nombre_completo="Cliente B1")
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    # 3 respuestas vía link público.
    for c in (cliente_a1, cliente_a2, cliente_b1):
        token = sign_link_token(settings, cliente_id=c.id)
        resp = await app_client.post(
            f"/api/publico/c/{token}/respuesta",
            json={"accion": "confirmo", "observacion": f"obs-{c.nombre_completo}"},
        )
        assert resp.status_code == 200

    # Admin de A lista sus pedidos.
    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin_a.id, empresa_id=empresa_a.id, rol="admin"
    )
    resp = await app_client.get("/api/pedidos", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    nombres = sorted(item["cliente_nombre"] for item in body["items"])
    assert nombres == ["Cliente A1", "Cliente A2"]
    assert all(item["accion"] == "confirmo" for item in body["items"])


@pytest.mark.integration
async def test_listar_pedidos_sin_auth_401(
    app_client: AsyncClient, _override_settings: None
) -> None:
    resp = await app_client.get("/api/pedidos")
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.req("REQ-PED-004")
async def test_stats_pedidos(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente_a = await make_cliente(db_session, empresa=empresa, nombre_completo="A")
    cliente_b = await make_cliente(db_session, empresa=empresa, nombre_completo="B")
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    for c, accion in ((cliente_a, "confirmo"), (cliente_b, "rechazo")):
        token = sign_link_token(settings, cliente_id=c.id)
        await app_client.post(f"/api/publico/c/{token}/respuesta", json={"accion": accion})

    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin"
    )
    resp = await app_client.get("/api/pedidos/stats", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pedidos_hoy"] == 2
    assert body["confirmados_hoy"] == 1
    assert body["pedidos_semana"] == 2
    assert body["clientes_activos"] == 2


@pytest.mark.integration
@pytest.mark.req("REQ-PED-005")
async def test_export_csv(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente = await make_cliente(db_session, empresa=empresa, nombre_completo="Juan Pérez")
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    token = sign_link_token(settings, cliente_id=cliente.id)
    await app_client.post(
        f"/api/publico/c/{token}/respuesta",
        json={"accion": "confirmo", "observacion": "Después de las 15hs"},
    )

    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin"
    )
    resp = await app_client.get(
        "/api/pedidos/export.csv", headers={"Authorization": f"Bearer {tok}"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    body = resp.text
    assert body.splitlines()[0].startswith("Cliente,")
    assert "Juan Pérez" in body
    assert "Después de las 15hs" in body
    assert "confirmo" in body


@pytest.mark.integration
@pytest.mark.req("REQ-PED-006")
async def test_pendientes_lista_solo_sin_respuesta(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """Genera 2 links (A y B), A responde y B no. Pendientes muestra sólo B."""
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente_a = await make_cliente(db_session, empresa=empresa, nombre_completo="Cliente A")
    cliente_b = await make_cliente(db_session, empresa=empresa, nombre_completo="Cliente B")

    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin"
    )
    headers = {"Authorization": f"Bearer {tok}"}

    r1 = await app_client.post(f"/api/clientes/{cliente_a.id}/generar-link", headers=headers)
    assert r1.status_code == 200
    r2 = await app_client.post(f"/api/clientes/{cliente_b.id}/generar-link", headers=headers)
    assert r2.status_code == 200

    # Sólo A responde.
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))
    token_a = sign_link_token(settings, cliente_id=cliente_a.id)
    rresp = await app_client.post(
        f"/api/publico/c/{token_a}/respuesta", json={"accion": "confirmo"}
    )
    assert rresp.status_code == 200

    resp = await app_client.get("/api/pedidos/pendientes", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["cliente_nombre"] == "Cliente B"


@pytest.mark.integration
@pytest.mark.req("REQ-PED-003")
async def test_listar_pedidos_filtra_por_accion(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente_a = await make_cliente(db_session, empresa=empresa, nombre_completo="A")
    cliente_b = await make_cliente(db_session, empresa=empresa, nombre_completo="B")
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    for c, accion in ((cliente_a, "confirmo"), (cliente_b, "rechazo")):
        token = sign_link_token(settings, cliente_id=c.id)
        await app_client.post(f"/api/publico/c/{token}/respuesta", json={"accion": accion})

    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin"
    )
    headers = {"Authorization": f"Bearer {tok}"}

    confirmados = (await app_client.get("/api/pedidos?accion=confirmo", headers=headers)).json()
    assert confirmados["total"] == 1
    assert confirmados["items"][0]["cliente_nombre"] == "A"

    rechazos = (await app_client.get("/api/pedidos?accion=rechazo", headers=headers)).json()
    assert rechazos["total"] == 1
    assert rechazos["items"][0]["cliente_nombre"] == "B"


@pytest.mark.integration
async def test_listar_pedidos_paginacion(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    clientes = [
        await make_cliente(db_session, empresa=empresa, nombre_completo=f"Cliente {i}")
        for i in range(5)
    ]
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    for c in clientes:
        token = sign_link_token(settings, cliente_id=c.id)
        await app_client.post(f"/api/publico/c/{token}/respuesta", json={"accion": "confirmo"})

    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin"
    )
    resp = await app_client.get(
        "/api/pedidos?limit=2&offset=1",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2


@pytest.mark.integration
@pytest.mark.req("REQ-PED-003")
async def test_listar_pedidos_busca_por_nombre(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente_a = await make_cliente(db_session, empresa=empresa, nombre_completo="Juan Lopez")
    cliente_b = await make_cliente(db_session, empresa=empresa, nombre_completo="Maria Garcia")
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    for c in (cliente_a, cliente_b):
        token = sign_link_token(settings, cliente_id=c.id)
        await app_client.post(f"/api/publico/c/{token}/respuesta", json={"accion": "confirmo"})

    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin"
    )
    headers = {"Authorization": f"Bearer {tok}"}

    # Búsqueda por nombre.
    r = (await app_client.get("/api/pedidos?q=Lopez", headers=headers)).json()
    assert r["total"] == 1
    assert r["items"][0]["cliente_nombre"] == "Juan Lopez"

    # Case-insensitive (ILIKE).
    r = (await app_client.get("/api/pedidos?q=marIA", headers=headers)).json()
    assert r["total"] == 1
    assert r["items"][0]["cliente_nombre"] == "Maria Garcia"

    # Sin matches.
    r = (await app_client.get("/api/pedidos?q=NoExiste", headers=headers)).json()
    assert r["total"] == 0
