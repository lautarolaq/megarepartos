"""Tests unitarios de tokens broadcast (`infra.auth`) + normalizador de teléfono.

Cubren:
- Firma/verificación de broadcast tokens (mismo formato `id.exp.sig` que los
  tokens personales, pero con prefijo "broadcast:" en el HMAC, así los tokens
  no son intercambiables entre sí).
- normalizar_telefono con variantes habituales de AR (con/sin 0 inicial,
  con/sin 15, con/sin 9 de celular).
"""

from __future__ import annotations

import uuid

import pytest

from megarepartos.config import Settings
from megarepartos.domain.clientes import normalizar_telefono
from megarepartos.infra.auth import (
    sign_broadcast_token,
    sign_link_token,
    verify_broadcast_token,
    verify_link_token,
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


# Broadcast tokens ----------------------------------------------------------


@pytest.mark.unit
def test_sign_broadcast_token_roundtrip(settings: Settings) -> None:
    empresa_id = uuid.uuid4()
    token = sign_broadcast_token(settings, empresa_id=empresa_id)
    parsed = verify_broadcast_token(settings, token)
    assert parsed == empresa_id


@pytest.mark.unit
def test_broadcast_token_rechaza_link_token(settings: Settings) -> None:
    """Un token personal NO debe validar como broadcast (prefijo distinto)."""
    cliente_id = uuid.uuid4()
    link_token = sign_link_token(settings, cliente_id=cliente_id)
    with pytest.raises(ApiError) as exc:
        verify_broadcast_token(settings, link_token)
    assert exc.value.code == ErrorCode.VALIDACION_INPUT


@pytest.mark.unit
def test_link_token_rechaza_broadcast_token(settings: Settings) -> None:
    """Y vice-versa: un broadcast token no debe validar como link personal."""
    empresa_id = uuid.uuid4()
    broadcast_token = sign_broadcast_token(settings, empresa_id=empresa_id)
    with pytest.raises(ApiError) as exc:
        verify_link_token(settings, broadcast_token)
    assert exc.value.code == ErrorCode.VALIDACION_INPUT


@pytest.mark.unit
def test_broadcast_token_expira(settings: Settings) -> None:
    empresa_id = uuid.uuid4()
    token = sign_broadcast_token(settings, empresa_id=empresa_id, ttl_seconds=-1)
    # Esperar 1s no es necesario porque ttl_seconds=-1 ya queda en el pasado.
    with pytest.raises(ApiError) as exc:
        verify_broadcast_token(settings, token)
    assert exc.value.code == ErrorCode.VALIDACION_INPUT
    assert "expir" in exc.value.message.lower()


@pytest.mark.unit
def test_broadcast_token_firma_invalida(settings: Settings) -> None:
    empresa_id = uuid.uuid4()
    token = sign_broadcast_token(settings, empresa_id=empresa_id)
    # Cambiar el último char
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
    with pytest.raises(ApiError) as exc:
        verify_broadcast_token(settings, tampered)
    assert exc.value.code == ErrorCode.VALIDACION_INPUT


# normalizar_telefono -------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,esperado",
    [
        # AR cellular con código de área 3 dígitos (Córdoba)
        ("351 770 7209", "+5493517707209"),
        ("3517707209", "+5493517707209"),
        ("0351 770 7209", "+5493517707209"),
        ("0351 15 770 7209", "+5493517707209"),
        ("+54 9 351 770 7209", "+5493517707209"),
        ("+54 351 770 7209", "+5493517707209"),  # sin 9 → lo agregamos
        ("+549 351 770 7209", "+5493517707209"),
        # Buenos Aires (2 dígitos de área)
        ("+54 11 1234 5678", "+5491112345678"),
        ("11 15 1234 5678", "+5491112345678"),
        # Con paréntesis y guiones
        ("(0351) 15-770-7209", "+5493517707209"),
        # Con puntos (forma común copy/paste)
        ("+54.351.770.7209", "+5493517707209"),
    ],
)
def test_normalizar_telefono_ar(raw: str, esperado: str) -> None:
    assert normalizar_telefono(raw) == esperado


@pytest.mark.unit
def test_normalizar_telefono_extranjero_se_respeta(settings: Settings) -> None:
    """Si ya viene con +XX donde XX != 54, no lo tocamos."""
    assert normalizar_telefono("+1 415 555 0100") == "+14155550100"


@pytest.mark.unit
def test_normalizar_telefono_vacio_falla(settings: Settings) -> None:
    with pytest.raises(ApiError) as exc:
        normalizar_telefono("")
    assert exc.value.code == ErrorCode.VALIDACION_INPUT
