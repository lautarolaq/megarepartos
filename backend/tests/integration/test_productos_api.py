"""Tests de integración del CRUD `/api/productos` (TASK-008 / REQ-PROD-001..012).

Cubren happy paths, auth, roles, aislamiento multi-tenant via los helpers
de `_isolation_helpers.py`.
"""

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
from megarepartos.models.producto import Envase, Producto
from tests.factories import make_empresa, make_producto, make_usuario
from tests.integration._isolation_helpers import (
    assert_endpoint_isolated_detail_404,
    assert_endpoint_isolated_get,
    assert_endpoint_isolated_mutation_404,
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


async def _token_for(
    settings: Settings, *, usuario_id: uuid.UUID, empresa_id: uuid.UUID, rol: str
) -> str:
    tok, _ = issue_access_token(
        settings=settings, usuario_id=usuario_id, empresa_id=empresa_id, rol=rol
    )
    return tok


async def _seed_admin(db_session: AsyncSession) -> tuple[object, object]:
    """Crea empresa + usuario admin y deja el tenant context seteado.

    Devuelve `(Empresa, Usuario)` pero anotamos `object` para no importar models
    en tests (no es un router pero respetamos el patrón).
    """
    empresa = await make_empresa(db_session, nombre=f"E-{uuid.uuid4().hex[:6]}")
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    return empresa, admin


# ---- REQ-PROD-001 / 002 ----


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-001")
@pytest.mark.req("REQ-PROD-002")
@pytest.mark.req("REQ-REPO-002")
@pytest.mark.req("REQ-REPO-003")
async def test_REQ_PROD_001_002_listado_ordenado_y_filtro_activo(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    # Crear con orden_display intercalado para verificar ordering.
    await make_producto(db_session, empresa=empresa, nombre="Z-3", orden_display=10)
    await make_producto(db_session, empresa=empresa, nombre="A-1", orden_display=0)
    inactivo = await make_producto(
        db_session, empresa=empresa, nombre="X-inactivo", activo=False, orden_display=5
    )

    token = await _token_for(settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Sin filtro: todos. Ordenados por (orden_display ASC, nombre ASC).
    resp = await app_client.get("/api/productos", headers=headers)
    assert resp.status_code == 200
    nombres = [p["nombre"] for p in resp.json()["items"]]
    assert nombres == ["A-1", "X-inactivo", "Z-3"]

    # activo=true → 2 activos.
    resp = await app_client.get("/api/productos?activo=true", headers=headers)
    nombres_activos = {p["nombre"] for p in resp.json()["items"]}
    assert nombres_activos == {"A-1", "Z-3"}

    # activo=false → solo inactivos.
    resp = await app_client.get("/api/productos?activo=false", headers=headers)
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(inactivo.id)


# ---- REQ-PROD-003 + isolation listado ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-PROD-003")
@pytest.mark.req("REQ-REPO-001")
async def test_REQ_PROD_003_detalle_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    await assert_endpoint_isolated_detail_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url_template="/api/productos/{id}",
        factory=lambda s, e: make_producto(s, empresa=e),
    )


@pytest.mark.integration
@pytest.mark.isolation
async def test_listado_productos_aislamiento_isolation(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """REQ-MT-009 aplicado a `GET /api/productos`. Cubre el chequeo CI
    `check_endpoint_isolation` para este endpoint."""
    await assert_endpoint_isolated_get(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        url="/api/productos",
        factory=lambda s, e: make_producto(s, empresa=e),
        id_extractor=lambda body: {uuid.UUID(p["id"]) for p in body["items"]},
    )


# ---- REQ-PROD-004 / 005 ----


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-004")
async def test_REQ_PROD_004_post_crea_y_devuelve_201(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    token = await _token_for(settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin")

    resp = await app_client.post(
        "/api/productos",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "nombre": "Bidón 20L",
            "es_retornable": True,
            "precio_unitario_default": "1500.00",
            "orden_display": 1,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre"] == "Bidón 20L"
    assert body["es_retornable"] is True
    assert body["activo"] is True

    # El producto realmente está en la DB.
    en_db = (
        await db_session.execute(select(Producto).where(Producto.id == uuid.UUID(body["id"])))
    ).scalar_one()
    assert en_db.empresa_id == empresa.id


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-005")
async def test_REQ_PROD_005_post_sin_nombre_400(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    token = await _token_for(settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin")

    resp = await app_client.post(
        "/api/productos",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "", "es_retornable": False},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDACION_INPUT"


# ---- REQ-PROD-006 ----


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-006")
@pytest.mark.req("REQ-ROL-005")
async def test_REQ_PROD_006_post_como_operador_403(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    operador = await make_usuario(db_session, empresa=empresa, rol="operador")
    token = await _token_for(
        settings, usuario_id=operador.id, empresa_id=empresa.id, rol="operador"
    )

    resp = await app_client.post(
        "/api/productos",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Soda 1.5L", "es_retornable": True},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISO_DENEGADO"


# ---- REQ-PROD-007 / 008 ----


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-007")
async def test_REQ_PROD_007_patch_solo_cambia_provided(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    producto = await make_producto(db_session, empresa=empresa, nombre="Original", orden_display=5)
    token = await _token_for(settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin")

    resp = await app_client.patch(
        f"/api/productos/{producto.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Nuevo"},  # solo nombre
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nombre"] == "Nuevo"
    assert body["orden_display"] == 5  # no cambió


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-PROD-008")
async def test_REQ_PROD_008_patch_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    await assert_endpoint_isolated_mutation_404(
        app_client=app_client,
        db_session=db_session,
        settings=settings,
        method="PATCH",
        url_template="/api/productos/{id}",
        factory=lambda s, e: make_producto(s, empresa=e),
        payload={"nombre": "Hackeado"},
    )


# ---- REQ-PROD-009 / 010 ----


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-009")
@pytest.mark.req("REQ-PROD-010")
async def test_REQ_PROD_009_010_delete_soft_e_idempotente(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    producto = await make_producto(db_session, empresa=empresa)
    token = await _token_for(settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Primer DELETE: 204 + soft delete.
    r1 = await app_client.delete(f"/api/productos/{producto.id}", headers=headers)
    assert r1.status_code == 204

    en_db = (
        await db_session.execute(select(Producto).where(Producto.id == producto.id))
    ).scalar_one()
    assert en_db.activo is False

    # Segundo DELETE: idempotente, también 204.
    r2 = await app_client.delete(f"/api/productos/{producto.id}", headers=headers)
    assert r2.status_code == 204


# ---- REQ-PROD-011 ----


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-011")
async def test_REQ_PROD_011_eventos_generados(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    token = await _token_for(settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Crear → modificar → borrar.
    create_resp = await app_client.post("/api/productos", headers=headers, json={"nombre": "Test"})
    producto_id = create_resp.json()["id"]
    await app_client.patch(
        f"/api/productos/{producto_id}", headers=headers, json={"nombre": "Renombrado"}
    )
    await app_client.delete(f"/api/productos/{producto_id}", headers=headers)

    eventos = (
        (
            await db_session.execute(
                select(EventoDominio)
                .where(EventoDominio.entidad_id == uuid.UUID(producto_id))
                .order_by(EventoDominio.fecha.asc())
            )
        )
        .scalars()
        .all()
    )
    acciones = [e.accion for e in eventos]
    assert acciones == ["creado", "modificado", "desactivado"]
    # El evento de modificación incluye el diff de `nombre`.
    diff = eventos[1].detalles_jsonb["diff"]
    assert diff["nombre"]["de"] == "Test"
    assert diff["nombre"]["a"] == "Renombrado"


# ---- REQ-PROD-012 ----


@pytest.mark.integration
@pytest.mark.req("REQ-PROD-012")
async def test_REQ_PROD_012_envase_ajeno_422(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa_a, admin_a = await _seed_admin(db_session)

    # Crear envase para empresa B (otra empresa).
    empresa_b = await make_empresa(db_session, nombre="OtraB")
    usuario_b = await make_usuario(db_session, empresa=empresa_b)
    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    envase_b = Envase(empresa_id=empresa_b.id, nombre="Envase de B")
    db_session.add(envase_b)
    await db_session.flush()

    # Volver a empresa A.
    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=admin_a.id)

    token = await _token_for(settings, usuario_id=admin_a.id, empresa_id=empresa_a.id, rol="admin")
    resp = await app_client.post(
        "/api/productos",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "X", "envase_id": str(envase_b.id)},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDACION_SEMANTICA"


# ---- Audit (TASK-005 REQ-AUD-002 / 003) ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUD-001")
@pytest.mark.req("REQ-AUD-002")
@pytest.mark.req("REQ-AUD-003")
async def test_REQ_AUD_001_002_003_evento_lleva_request_id_ip_ua(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa, admin = await _seed_admin(db_session)
    token = await _token_for(settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin")

    resp = await app_client.post(
        "/api/productos",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Request-ID": "test-req-abc-123",
            "User-Agent": "PytestClient/1.0",
        },
        json={"nombre": "Audited"},
    )
    assert resp.status_code == 201
    assert resp.headers["x-request-id"] == "test-req-abc-123"

    producto_id = uuid.UUID(resp.json()["id"])
    evento = (
        await db_session.execute(
            select(EventoDominio).where(EventoDominio.entidad_id == producto_id)
        )
    ).scalar_one()
    assert evento.user_agent == "PytestClient/1.0"
    assert evento.detalles_jsonb["request_id"] == "test-req-abc-123"
