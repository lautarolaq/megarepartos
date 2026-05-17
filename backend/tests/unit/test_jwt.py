"""Tests unitarios del módulo `infra.auth` (JWT + state firmado).

No tocan DB ni Google. Cubren REQ-AUTH-011 y REQ-AUTH-012 + edge cases del
firmador de state.
"""

from __future__ import annotations

import time
import uuid

import pytest
from jose import jwt

from megarepartos.config import Settings
from megarepartos.infra.auth import (
    STATE_TTL_SECONDS,
    decode_token,
    issue_access_token,
    issue_refresh_token,
    sign_state,
    verify_state,
)
from megarepartos.infra.errors import ApiError, ErrorCode


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-cualquiera",
        jwt_algorithm="HS256",
        jwt_access_ttl_min=60,
        jwt_refresh_ttl_days=14,
    )


@pytest.mark.unit
@pytest.mark.req("REQ-AUTH-012")
def test_REQ_AUTH_012_jwt_claims_incluyen_sub_empresa_id_rol_type(
    settings: Settings,
) -> None:
    """El JWT emitido incluye exactamente los claims requeridos."""
    usuario_id = uuid.uuid4()
    empresa_id = uuid.uuid4()
    token, _ = issue_access_token(
        settings=settings,
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        rol="admin",
    )
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert decoded["sub"] == str(usuario_id)
    assert decoded["empresa_id"] == str(empresa_id)
    assert decoded["rol"] == "admin"
    assert decoded["type"] == "access"
    assert "iat" in decoded
    assert "exp" in decoded
    assert decoded["exp"] > decoded["iat"]


@pytest.mark.unit
@pytest.mark.req("REQ-AUTH-011")
def test_REQ_AUTH_011_access_token_expira_segun_settings(settings: Settings) -> None:
    """`expires_in` devuelto coincide con `jwt_access_ttl_min * 60`."""
    _, expires_in = issue_access_token(
        settings=settings,
        usuario_id=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        rol="admin",
    )
    assert expires_in == settings.jwt_access_ttl_min * 60


@pytest.mark.unit
@pytest.mark.req("REQ-AUTH-011")
def test_REQ_AUTH_011_refresh_token_expira_segun_settings(settings: Settings) -> None:
    """`expires_in` del refresh coincide con `jwt_refresh_ttl_days * 86400`."""
    _, expires_in = issue_refresh_token(
        settings=settings,
        usuario_id=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        rol="admin",
    )
    assert expires_in == settings.jwt_refresh_ttl_days * 24 * 60 * 60


@pytest.mark.unit
def test_decode_token_round_trip(settings: Settings) -> None:
    """issue → decode devuelve los mismos UUIDs."""
    sub = uuid.uuid4()
    emp = uuid.uuid4()
    token, _ = issue_access_token(settings=settings, usuario_id=sub, empresa_id=emp, rol="operador")
    claims = decode_token(token, settings=settings, expected_type="access")
    assert claims.sub == sub
    assert claims.empresa_id == emp
    assert claims.rol == "operador"
    assert claims.type == "access"


@pytest.mark.unit
def test_decode_token_con_tipo_incorrecto_falla(settings: Settings) -> None:
    """Refresh token decodificado como access debe fallar (REQ-AUTH-010)."""
    token, _ = issue_refresh_token(
        settings=settings,
        usuario_id=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        rol="admin",
    )
    with pytest.raises(ApiError) as exc:
        decode_token(token, settings=settings, expected_type="access")
    assert exc.value.code == ErrorCode.AUTH_INVALID


@pytest.mark.unit
def test_decode_token_con_firma_mala_falla(settings: Settings) -> None:
    """Cambiar el secret invalida el token."""
    token, _ = issue_access_token(
        settings=settings,
        usuario_id=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        rol="admin",
    )
    other = Settings(jwt_secret="otro-secret", jwt_algorithm="HS256")
    with pytest.raises(ApiError) as exc:
        decode_token(token, settings=other, expected_type="access")
    assert exc.value.code == ErrorCode.AUTH_INVALID


@pytest.mark.unit
def test_state_signer_round_trip(settings: Settings) -> None:
    state = sign_state(settings)
    verify_state(settings, state)  # no excepción


@pytest.mark.unit
def test_state_firma_modificada_falla(settings: Settings) -> None:
    state = sign_state(settings)
    tampered = state[:-1] + ("0" if state[-1] != "0" else "1")
    with pytest.raises(ApiError) as exc:
        verify_state(settings, tampered)
    assert exc.value.code == ErrorCode.VALIDACION_INPUT


@pytest.mark.unit
def test_state_formato_invalido_falla(settings: Settings) -> None:
    with pytest.raises(ApiError):
        verify_state(settings, "no-tiene-puntos")


@pytest.mark.unit
def test_state_expirado_falla(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    """Backdating: forzamos el timestamp del state a ser viejo."""
    old_ts = int(time.time()) - STATE_TTL_SECONDS - 60

    monkeypatch.setattr("megarepartos.infra.auth._now_ts", lambda: old_ts)
    state = sign_state(settings)

    monkeypatch.setattr("megarepartos.infra.auth._now_ts", lambda: old_ts + STATE_TTL_SECONDS + 60)
    with pytest.raises(ApiError):
        verify_state(settings, state)
