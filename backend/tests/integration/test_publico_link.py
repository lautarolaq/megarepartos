"""Tests de integración del link público (TASK-020-022 / REQ-LINK-001..008)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.infra.auth import (
    issue_access_token,
    sign_link_token,
    verify_link_token,
)
from megarepartos.infra.db import set_tenant_context
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.main import app
from tests.factories import make_cliente, make_empresa, make_usuario


@pytest_asyncio.fixture
async def settings() -> Settings:
    return Settings(jwt_secret="test-secret-link", jwt_algorithm="HS256")


@pytest_asyncio.fixture
async def _override_settings(settings: Settings) -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


# ---- Unit del firmador ----


@pytest.mark.unit
@pytest.mark.req("REQ-LINK-001")
@pytest.mark.req("REQ-LINK-002")
def test_REQ_LINK_001_002_sign_verify_round_trip() -> None:
    s = Settings(jwt_secret="x")
    cli = uuid.uuid4()
    token = sign_link_token(s, cliente_id=cli)
    assert verify_link_token(s, token) == cli


@pytest.mark.unit
def test_link_token_firma_invalida_falla() -> None:
    s = Settings(jwt_secret="x")
    token = sign_link_token(s, cliente_id=uuid.uuid4())
    # Cambiar el último char de la firma.
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
    with pytest.raises(ApiError) as exc:
        verify_link_token(s, tampered)
    assert exc.value.code == ErrorCode.VALIDACION_INPUT


@pytest.mark.unit
def test_link_token_expirado_falla() -> None:
    s = Settings(jwt_secret="x")
    token = sign_link_token(s, cliente_id=uuid.uuid4(), ttl_seconds=-1)
    with pytest.raises(ApiError):
        verify_link_token(s, token)


@pytest.mark.unit
def test_link_token_otro_secret_falla() -> None:
    s1 = Settings(jwt_secret="x")
    s2 = Settings(jwt_secret="y")
    token = sign_link_token(s1, cliente_id=uuid.uuid4())
    with pytest.raises(ApiError):
        verify_link_token(s2, token)


# ---- Integration: endpoints públicos ----


@pytest.mark.integration
@pytest.mark.req("REQ-LINK-003")
async def test_REQ_LINK_003_get_publico_devuelve_cliente_y_empresa(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session, nombre="Sodería Las Marías")
    admin = await make_usuario(db_session, empresa=empresa)
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente = await make_cliente(
        db_session, empresa=empresa, nombre_completo="Juan Pérez", telefono="+5435155"
    )

    # El endpoint público hace RESET ROLE internamente.
    token = sign_link_token(settings, cliente_id=cliente.id)
    resp = await app_client.get(f"/api/publico/c/{token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["empresa"]["nombre"] == "Sodería Las Marías"
    assert body["cliente"]["nombre_completo"] == "Juan Pérez"


@pytest.mark.integration
@pytest.mark.req("REQ-LINK-004")
async def test_REQ_LINK_004_token_invalido_400(
    app_client: AsyncClient, _override_settings: None
) -> None:
    resp = await app_client.get("/api/publico/c/no-es-un-token")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDACION_INPUT"


@pytest.mark.integration
@pytest.mark.req("REQ-LINK-005")
async def test_REQ_LINK_005_post_respuesta_ok(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa)
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente = await make_cliente(db_session, empresa=empresa)
    # Volver a rol megarepartos_app por defecto del fixture — el endpoint RESETea.
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    token = sign_link_token(settings, cliente_id=cliente.id)
    resp = await app_client.post(
        f"/api/publico/c/{token}/respuesta",
        json={"accion": "confirmo", "datos": {"nota": "después de las 15"}},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.integration
@pytest.mark.req("REQ-LINK-008")
async def test_REQ_LINK_008_admin_genera_link(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    empresa = await make_empresa(db_session)
    admin = await make_usuario(db_session, empresa=empresa, rol="admin")
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=admin.id)
    cliente = await make_cliente(db_session, empresa=empresa)

    tok, _ = issue_access_token(
        settings=settings, usuario_id=admin.id, empresa_id=empresa.id, rol="admin"
    )

    resp = await app_client.post(
        f"/api/clientes/{cliente.id}/generar-link",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "/c/" in body["url"]
    assert body["expira_en_dias"] == 30
    # El token devuelto debe verify correctamente.
    assert verify_link_token(settings, body["token"]) == cliente.id


@pytest.mark.integration
async def test_admin_generar_link_cliente_ajeno_404(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _override_settings: None,
) -> None:
    """Admin de empresa A pide link de cliente de empresa B → 404."""
    empresa_a = await make_empresa(db_session, nombre="A")
    admin_a = await make_usuario(db_session, empresa=empresa_a, rol="admin")
    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_b = await make_usuario(db_session, empresa=empresa_b)
    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    cliente_b = await make_cliente(db_session, empresa=empresa_b)

    tok, _ = issue_access_token(
        settings=settings,
        usuario_id=admin_a.id,
        empresa_id=empresa_a.id,
        rol="admin",
    )
    resp = await app_client.post(
        f"/api/clientes/{cliente_b.id}/generar-link",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert resp.status_code == 404
