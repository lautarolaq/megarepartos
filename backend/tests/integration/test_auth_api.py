"""Tests de integración del flow de auth.

Cubren REQ-AUTH-001..010 y REQ-EMP-001..006 a través del API real (httpx →
FastAPI app → DB en testcontainer).

`Google` se mockea sobreescribiendo `auth_infra.verify_google_id_token` y
`api.auth._exchange_code_for_id_token` para que el callback no haga calls de red.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.api import auth as api_auth
from megarepartos.config import Settings, get_settings
from megarepartos.infra import auth as auth_infra
from megarepartos.infra.auth import (
    REFRESH_COOKIE_NAME,
    GoogleProfile,
    issue_access_token,
    issue_refresh_token,
    sign_state,
)
from megarepartos.main import app
from megarepartos.models.empresa import Empresa
from megarepartos.models.usuario import Usuario
from tests.factories import make_empresa, make_usuario


@pytest_asyncio.fixture
async def settings() -> Settings:
    """Settings con credenciales OAuth dummy y secret fijo."""
    return Settings(
        jwt_secret="test-secret-int",
        jwt_algorithm="HS256",
        jwt_access_ttl_min=60,
        jwt_refresh_ttl_days=14,
        google_oauth_client_id="dummy-client",
        google_oauth_client_secret="dummy-secret",
        google_oauth_redirect_url="http://localhost:8000/api/auth/google/callback",
    )


@pytest_asyncio.fixture
async def _setup_oauth(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Inyecta Settings de test (vía FastAPI override) y mockea Google."""
    app.dependency_overrides[get_settings] = lambda: settings

    async def _fake_exchange(*, code: str, settings: Settings) -> str:
        return f"fake-id-token-for-{code}"

    monkeypatch.setattr(api_auth, "_exchange_code_for_id_token", _fake_exchange)
    yield
    app.dependency_overrides.pop(get_settings, None)


def _mock_google_verifier(profile: GoogleProfile) -> Callable[[str], GoogleProfile]:
    def _verifier(_id_token: str) -> GoogleProfile:
        return profile

    return _verifier


# ---- REQ-AUTH-001 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-001")
async def test_REQ_AUTH_001_url_de_autorizacion_incluye_state_firmado(
    app_client: AsyncClient, _setup_oauth: None
) -> None:
    resp = await app_client.get("/api/auth/google/url")
    assert resp.status_code == 200
    body = resp.json()
    assert "url" in body
    assert "state=" in body["url"]
    assert "client_id=dummy-client" in body["url"]


# ---- REQ-AUTH-002 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-002")
async def test_REQ_AUTH_002_callback_con_code_valido_emite_access_token(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    _setup_oauth: None,
) -> None:
    profile = GoogleProfile(sub="g-sub-001", email="alice@example.com", nombre="Alice")
    monkeypatch.setattr(auth_infra, "verify_google_id_token", _mock_google_verifier(profile))
    state = sign_state(settings)

    resp = await app_client.get(
        "/api/auth/google/callback",
        params={"code": "valid-code", "state": state},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 307)
    assert "access_token=" in resp.headers["location"]
    assert REFRESH_COOKIE_NAME in resp.headers.get("set-cookie", "")

    # El usuario y la empresa se crearon.
    usuario = (
        await db_session.execute(select(Usuario).where(Usuario.email == "alice@example.com"))
    ).scalar_one()
    assert usuario.rol == "admin"
    assert usuario.activo


# ---- REQ-AUTH-003 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-003")
async def test_REQ_AUTH_003_callback_con_state_invalido_devuelve_400(
    app_client: AsyncClient, _setup_oauth: None
) -> None:
    resp = await app_client.get(
        "/api/auth/google/callback",
        params={"code": "x", "state": "estado-no-firmado"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDACION_INPUT"


# ---- REQ-AUTH-004 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-004")
async def test_REQ_AUTH_004_refresh_con_cookie_valida_emite_nuevo_access(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _setup_oauth: None,
) -> None:
    empresa = await make_empresa(db_session)
    usuario = await make_usuario(db_session, empresa=empresa)

    refresh, _ = issue_refresh_token(
        settings=settings,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
        rol=usuario.rol,
    )
    app_client.cookies.set(REFRESH_COOKIE_NAME, refresh)

    resp = await app_client.post("/api/auth/refresh")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_access_ttl_min * 60
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 20


# ---- REQ-AUTH-005 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-005")
async def test_REQ_AUTH_005_refresh_sin_cookie_devuelve_401(
    app_client: AsyncClient, _setup_oauth: None
) -> None:
    resp = await app_client.post("/api/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_REQUIRED"


# ---- REQ-AUTH-006 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-006")
async def test_REQ_AUTH_006_refresh_con_token_expirado_devuelve_401(
    app_client: AsyncClient, _setup_oauth: None
) -> None:
    # Token firmado con otro secret = inválido (equivalente operacional a expirado).
    bad_settings = Settings(jwt_secret="otro-secret-distinto", jwt_algorithm="HS256")
    bad_refresh, _ = issue_refresh_token(
        settings=bad_settings,
        usuario_id=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        rol="admin",
    )
    app_client.cookies.set(REFRESH_COOKIE_NAME, bad_refresh)

    resp = await app_client.post("/api/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_INVALID"


# ---- REQ-AUTH-007 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-007")
async def test_REQ_AUTH_007_logout_borra_cookie(
    app_client: AsyncClient, _setup_oauth: None
) -> None:
    app_client.cookies.set(REFRESH_COOKIE_NAME, "lo-que-sea")
    resp = await app_client.post("/api/auth/logout")
    assert resp.status_code == 204
    set_cookie = resp.headers.get("set-cookie", "")
    assert REFRESH_COOKIE_NAME in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie


# ---- REQ-AUTH-008 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-008")
async def test_REQ_AUTH_008_me_con_token_valido_devuelve_usuario_y_empresa(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _setup_oauth: None,
) -> None:
    empresa = await make_empresa(db_session, nombre="Sodería Las Marías")
    usuario = await make_usuario(db_session, empresa=empresa, email="ada@example.com", nombre="Ada")

    access, _ = issue_access_token(
        settings=settings,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
        rol=usuario.rol,
    )

    resp = await app_client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["usuario"]["email"] == "ada@example.com"
    assert body["usuario"]["nombre"] == "Ada"
    assert body["empresa"]["nombre"] == "Sodería Las Marías"


# ---- REQ-AUTH-009 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-009")
async def test_REQ_AUTH_009_me_sin_token_devuelve_401(
    app_client: AsyncClient, _setup_oauth: None
) -> None:
    resp = await app_client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_REQUIRED"


# ---- REQ-AUTH-010 ----


@pytest.mark.integration
@pytest.mark.req("REQ-AUTH-010")
async def test_REQ_AUTH_010_me_con_token_expirado_devuelve_401(
    app_client: AsyncClient, _setup_oauth: None
) -> None:
    # Token firmado con otro secret = inválido.
    bad_settings = Settings(jwt_secret="otro-secret", jwt_algorithm="HS256")
    access, _ = issue_access_token(
        settings=bad_settings,
        usuario_id=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        rol="admin",
    )
    resp = await app_client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_INVALID"


@pytest.mark.integration
async def test_me_con_token_de_tipo_refresh_falla(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    _setup_oauth: None,
) -> None:
    """Pasar un refresh como Bearer también devuelve 401 (REQ-AUTH-010)."""
    empresa = await make_empresa(db_session)
    usuario = await make_usuario(db_session, empresa=empresa)
    refresh, _ = issue_refresh_token(
        settings=settings,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
        rol=usuario.rol,
    )
    resp = await app_client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401


# ---- REQ-EMP-* (entrelazado con auth flow) ----


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-001")
async def test_REQ_EMP_001_primer_login_crea_empresa_y_usuario_admin(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    _setup_oauth: None,
) -> None:
    profile = GoogleProfile(sub="g-001", email="founder@example.com", nombre="Founder")
    monkeypatch.setattr(auth_infra, "verify_google_id_token", _mock_google_verifier(profile))
    state = sign_state(settings)

    resp = await app_client.get(
        "/api/auth/google/callback",
        params={"code": "x", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)

    usuario = (
        await db_session.execute(select(Usuario).where(Usuario.email == "founder@example.com"))
    ).scalar_one()
    assert usuario.rol == "admin"
    assert usuario.activo is True

    empresa = (
        await db_session.execute(select(Empresa).where(Empresa.id == usuario.empresa_id))
    ).scalar_one()
    assert "Founder" in empresa.nombre


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-002")
async def test_REQ_EMP_002_email_normalizado_a_lowercase(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    _setup_oauth: None,
) -> None:
    profile = GoogleProfile(sub="g-002", email="Mixed.CASE@Example.com", nombre="X")
    monkeypatch.setattr(auth_infra, "verify_google_id_token", _mock_google_verifier(profile))
    state = sign_state(settings)

    await app_client.get(
        "/api/auth/google/callback",
        params={"code": "x", "state": state},
        follow_redirects=False,
    )

    usuario = (
        await db_session.execute(select(Usuario).where(Usuario.email == "mixed.case@example.com"))
    ).scalar_one()
    assert usuario.email == "mixed.case@example.com"


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-003")
async def test_REQ_EMP_003_login_existente_actualiza_ultima_sesion(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    _setup_oauth: None,
) -> None:
    empresa = await make_empresa(db_session)
    usuario = await make_usuario(db_session, empresa=empresa, email="returning@example.com")
    await db_session.commit()
    assert usuario.ultima_sesion is None

    profile = GoogleProfile(sub="g-003", email="returning@example.com", nombre="Returning")
    monkeypatch.setattr(auth_infra, "verify_google_id_token", _mock_google_verifier(profile))
    state = sign_state(settings)

    await app_client.get(
        "/api/auth/google/callback",
        params={"code": "x", "state": state},
        follow_redirects=False,
    )
    await db_session.refresh(usuario)
    assert usuario.ultima_sesion is not None

    # No se creó otro usuario duplicado.
    todos = (
        (await db_session.execute(select(Usuario).where(Usuario.email == "returning@example.com")))
        .scalars()
        .all()
    )
    assert len(todos) == 1


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-004")
@pytest.mark.req("REQ-EMP-005")
async def test_REQ_EMP_004_005_empresa_y_usuario_inicializan_con_defaults(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    _setup_oauth: None,
) -> None:
    profile = GoogleProfile(sub="g-004", email="defaults@example.com", nombre="D")
    monkeypatch.setattr(auth_infra, "verify_google_id_token", _mock_google_verifier(profile))
    state = sign_state(settings)
    await app_client.get(
        "/api/auth/google/callback",
        params={"code": "x", "state": state},
        follow_redirects=False,
    )

    usuario = (
        await db_session.execute(select(Usuario).where(Usuario.email == "defaults@example.com"))
    ).scalar_one()
    assert usuario.rol == "admin"
    assert usuario.activo is True

    empresa = (
        await db_session.execute(select(Empresa).where(Empresa.id == usuario.empresa_id))
    ).scalar_one()
    assert empresa.estado_suscripcion == "trial"
    assert empresa.timezone == "America/Argentina/Cordoba"


@pytest.mark.integration
@pytest.mark.req("REQ-EMP-006")
async def test_REQ_EMP_006_login_con_usuario_inactivo_devuelve_409(
    app_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    _setup_oauth: None,
) -> None:
    empresa = await make_empresa(db_session)
    await make_usuario(db_session, empresa=empresa, email="inactivo@example.com", activo=False)
    await db_session.commit()

    profile = GoogleProfile(sub="g-006", email="inactivo@example.com", nombre="Inactivo")
    monkeypatch.setattr(auth_infra, "verify_google_id_token", _mock_google_verifier(profile))
    state = sign_state(settings)

    resp = await app_client.get(
        "/api/auth/google/callback",
        params={"code": "x", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICTO_ESTADO"
