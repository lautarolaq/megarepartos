"""Tests del dep `require_rol` (TASK-007 / REQ-ROL-001..004)."""

from __future__ import annotations

import uuid

import pytest

from megarepartos.infra.auth import TokenClaims, require_rol
from megarepartos.infra.errors import ApiError, ErrorCode


def _claims(rol: str) -> TokenClaims:
    return TokenClaims(
        sub=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        rol=rol,
        type="access",
        exp=9999999999,
        iat=0,
    )


@pytest.mark.unit
@pytest.mark.req("REQ-ROL-001")
def test_REQ_ROL_001_admin_pasa() -> None:
    checker = require_rol("admin")
    # El inner es síncrono; lo llamamos directo sin Depends.
    out = checker(_claims("admin"))
    assert out.rol == "admin"


@pytest.mark.unit
@pytest.mark.req("REQ-ROL-002")
def test_REQ_ROL_002_operador_es_rechazado() -> None:
    checker = require_rol("admin")
    with pytest.raises(ApiError) as exc:
        checker(_claims("operador"))
    assert exc.value.code == ErrorCode.PERMISO_DENEGADO
    assert exc.value.http_status == 403


@pytest.mark.unit
@pytest.mark.req("REQ-ROL-003")
def test_REQ_ROL_003_lista_de_roles_aceptados() -> None:
    checker = require_rol("admin", "operador")
    assert checker(_claims("admin")).rol == "admin"
    assert checker(_claims("operador")).rol == "operador"
    with pytest.raises(ApiError):
        checker(_claims("invitado"))


@pytest.mark.unit
@pytest.mark.req("REQ-ROL-004")
def test_REQ_ROL_004_mensaje_no_expone_roles_validos() -> None:
    checker = require_rol("admin", "operador")
    with pytest.raises(ApiError) as exc:
        checker(_claims("invitado"))
    assert "admin" not in exc.value.message
    assert "operador" not in exc.value.message


@pytest.mark.unit
def test_require_rol_sin_argumentos_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        require_rol()
