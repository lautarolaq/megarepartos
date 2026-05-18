"""Autenticación: JWT + verificación de Google id_token + dependencias FastAPI.

Responsabilidades:

1. **JWT** (`issue_access_token`, `issue_refresh_token`, `decode_token`):
   firma y verifica tokens HS256 con el secret de Settings.
2. **State signer** (`sign_state`, `verify_state`): HMAC sobre nonce+timestamp
   para evitar CSRF en el callback de OAuth.
3. **Google id_token verifier** (`verify_google_id_token`): wrapper sobre
   `google.oauth2.id_token` con inyección para tests.
4. **Dependencias FastAPI** (`current_claims`): expone los claims del JWT al
   router sin que el router tenga que importar de `models/`.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast

from fastapi import Depends, Header
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.infra.db import get_session, set_tenant_context
from megarepartos.infra.errors import ApiError, ErrorCode

# JWT ----------------------------------------------------------------------

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Claims decodificados de un JWT emitido por nosotros."""

    sub: uuid.UUID
    empresa_id: uuid.UUID
    rol: str
    type: TokenType
    exp: int
    iat: int


def _now_ts() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def _issue_token(
    *,
    settings: Settings,
    usuario_id: uuid.UUID,
    empresa_id: uuid.UUID,
    rol: str,
    type_: TokenType,
    ttl_seconds: int,
) -> str:
    iat = _now_ts()
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "empresa_id": str(empresa_id),
        "rol": rol,
        "type": type_,
        "iat": iat,
        "exp": iat + ttl_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def issue_access_token(
    *,
    settings: Settings,
    usuario_id: uuid.UUID,
    empresa_id: uuid.UUID,
    rol: str,
) -> tuple[str, int]:
    """Devuelve `(token, expires_in_seconds)`."""
    ttl = settings.jwt_access_ttl_min * 60
    token = _issue_token(
        settings=settings,
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        rol=rol,
        type_="access",
        ttl_seconds=ttl,
    )
    return token, ttl


def issue_refresh_token(
    *,
    settings: Settings,
    usuario_id: uuid.UUID,
    empresa_id: uuid.UUID,
    rol: str,
) -> tuple[str, int]:
    ttl = settings.jwt_refresh_ttl_days * 24 * 60 * 60
    token = _issue_token(
        settings=settings,
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        rol=rol,
        type_="refresh",
        ttl_seconds=ttl,
    )
    return token, ttl


def decode_token(token: str, *, settings: Settings, expected_type: TokenType) -> TokenClaims:
    """Decodifica + valida un JWT propio. Lanza `ApiError(AUTH_INVALID)` si algo falla."""
    try:
        raw = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ApiError(ErrorCode.AUTH_INVALID, "Token inválido o expirado.") from exc

    try:
        actual_type = raw["type"]
        if actual_type != expected_type:
            raise ApiError(
                ErrorCode.AUTH_INVALID,
                f"Tipo de token incorrecto (esperado {expected_type}, recibido {actual_type}).",
            )
        return TokenClaims(
            sub=uuid.UUID(raw["sub"]),
            empresa_id=uuid.UUID(raw["empresa_id"]),
            rol=raw["rol"],
            type=cast(TokenType, raw["type"]),
            exp=int(raw["exp"]),
            iat=int(raw["iat"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ApiError(ErrorCode.AUTH_INVALID, "Claims del token mal formados.") from exc


# Link tokens (motor 2: link público del cliente) --------------------------

LINK_TOKEN_DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días


def sign_link_token(
    settings: Settings,
    *,
    cliente_id: uuid.UUID,
    ttl_seconds: int = LINK_TOKEN_DEFAULT_TTL_SECONDS,
) -> str:
    """REQ-LINK-001: token firmado HMAC-SHA256.

    Formato `<cliente_id>.<expires_ts>.<sig>`. Stateless — no se persiste.
    """
    expires_ts = str(_now_ts() + ttl_seconds)
    payload = f"{cliente_id}.{expires_ts}"
    sig = hmac.new(
        settings.jwt_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{cliente_id}.{expires_ts}.{sig}"


def verify_link_token(settings: Settings, token: str) -> uuid.UUID:
    """REQ-LINK-002: valida firma + TTL. Devuelve `cliente_id`."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Token con formato inválido.")
    cliente_id_str, expires_ts_str, sig = parts
    expected_sig = hmac.new(
        settings.jwt_secret.encode(),
        f"{cliente_id_str}.{expires_ts_str}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, sig):
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Firma inválida.")
    try:
        expires_ts = int(expires_ts_str)
        cliente_id = uuid.UUID(cliente_id_str)
    except ValueError as exc:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Token mal formado.") from exc
    if _now_ts() > expires_ts:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "El link expiró.")
    return cliente_id


# Broadcast tokens — firmados sobre empresa_id en vez de cliente_id. La idea:
# un solo link "genérico" que sirve para una campaña broadcast en WhatsApp,
# y el cliente se identifica con su teléfono en la landing. Usamos un prefix
# "broadcast:" en el HMAC input para que estos tokens no sean intercambiables
# con los tokens personales por cliente.

BROADCAST_TOKEN_DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días


def sign_broadcast_token(
    settings: Settings,
    *,
    empresa_id: uuid.UUID,
    ttl_seconds: int = BROADCAST_TOKEN_DEFAULT_TTL_SECONDS,
) -> str:
    expires_ts = str(_now_ts() + ttl_seconds)
    payload = f"broadcast:{empresa_id}.{expires_ts}"
    sig = hmac.new(
        settings.jwt_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{empresa_id}.{expires_ts}.{sig}"


def verify_broadcast_token(settings: Settings, token: str) -> uuid.UUID:
    """Valida firma + TTL del broadcast token. Devuelve `empresa_id`."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Token con formato inválido.")
    empresa_id_str, expires_ts_str, sig = parts
    expected_sig = hmac.new(
        settings.jwt_secret.encode(),
        f"broadcast:{empresa_id_str}.{expires_ts_str}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, sig):
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Firma inválida.")
    try:
        expires_ts = int(expires_ts_str)
        empresa_id = uuid.UUID(empresa_id_str)
    except ValueError as exc:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Token mal formado.") from exc
    if _now_ts() > expires_ts:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "El link expiró.")
    return empresa_id


# State (CSRF) -------------------------------------------------------------

STATE_TTL_SECONDS = 10 * 60


def sign_state(settings: Settings, *, nonce: str | None = None) -> str:
    """Firma un nonce+timestamp con HMAC-SHA256. Devuelve `<nonce>.<ts>.<sig>`."""
    nonce = nonce or secrets.token_urlsafe(16)
    ts = str(_now_ts())
    sig = hmac.new(
        settings.jwt_secret.encode(),
        f"{nonce}.{ts}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{nonce}.{ts}.{sig}"


def verify_state(settings: Settings, state: str) -> None:
    """Valida un state firmado. Levanta `ApiError(VALIDACION_INPUT)` si algo falla."""
    parts = state.split(".")
    if len(parts) != 3:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "State con formato inválido.")
    nonce, ts_str, sig = parts
    expected_sig = hmac.new(
        settings.jwt_secret.encode(),
        f"{nonce}.{ts_str}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, sig):
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Firma de state inválida.")
    try:
        ts = int(ts_str)
    except ValueError as exc:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Timestamp de state inválido.") from exc
    if _now_ts() - ts > STATE_TTL_SECONDS:
        raise ApiError(ErrorCode.VALIDACION_INPUT, "State expirado.")


# Google id_token ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GoogleProfile:
    """Identidad mínima extraída del id_token de Google."""

    sub: str
    email: str
    nombre: str


GoogleVerifier = Callable[[str], GoogleProfile]


def _real_google_verifier(id_token_str: str) -> GoogleProfile:
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise ApiError(
            ErrorCode.EXTERNO_FALLO,
            "GOOGLE_OAUTH_CLIENT_ID no configurado.",
        )
    try:
        info = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.google_oauth_client_id,
        )
    except ValueError as exc:
        raise ApiError(ErrorCode.AUTH_INVALID, "id_token de Google inválido.") from exc
    return GoogleProfile(
        sub=info["sub"],
        email=info["email"],
        nombre=info.get("name") or info.get("email", "").split("@")[0],
    )


# Atributo del módulo, sobreescribible en tests para no llamar a Google.
verify_google_id_token: GoogleVerifier = _real_google_verifier


# Dependencias FastAPI -----------------------------------------------------


async def current_claims(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> TokenClaims:
    """Decodifica el `Authorization: Bearer ...` y devuelve los claims.

    Levanta `AUTH_REQUIRED` si no hay header, `AUTH_INVALID` si el token es malo.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(ErrorCode.AUTH_REQUIRED, "Falta el header Authorization Bearer.")
    token = authorization[7:].strip()
    return decode_token(token, settings=settings, expected_type="access")


async def authenticated_session(
    claims: Annotated[TokenClaims, Depends(current_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[AsyncSession]:
    """Sesión con tenant context seteado + commit-on-success.

    Los routers de negocio dependen de esta dep en vez de `get_session`. RLS
    de Postgres usa los session vars `app.empresa_id` y `app.usuario_id` para
    filtrar; sin esta dep no hay aislamiento (regla CLAUDE.md Backend #1).

    Si el endpoint termina sin excepción, commitea la transacción. Si levanta,
    el commit no se ejecuta y `session.close()` rollbackea (en `get_session`).
    """
    await set_tenant_context(
        session,
        empresa_id=claims.empresa_id,
        usuario_id=claims.sub,
    )
    yield session
    await session.commit()


def require_rol(*roles_permitidos: str) -> Callable[[TokenClaims], TokenClaims]:
    """Factory de dependencia FastAPI: exige que `claims.rol` esté en `roles_permitidos`.

    Uso:

        @router.post("/productos")
        async def crear(
            _admin: Annotated[TokenClaims, Depends(require_rol("admin"))],
            ...
        ): ...

    Levanta `ApiError(PERMISO_DENEGADO)` (403) si el rol no matchea. Mensaje
    genérico — no leakea qué roles serían válidos (REQ-ROL-004).
    """
    if not roles_permitidos:
        raise ValueError("require_rol necesita al menos un rol permitido.")

    permitidos = frozenset(roles_permitidos)

    def _checker(claims: Annotated[TokenClaims, Depends(current_claims)]) -> TokenClaims:
        if claims.rol not in permitidos:
            raise ApiError(
                ErrorCode.PERMISO_DENEGADO,
                "No tenés permiso para esta acción.",
            )
        return claims

    return _checker


# Cookie helpers -----------------------------------------------------------

REFRESH_COOKIE_NAME = "mr_refresh"


def refresh_cookie_kwargs(settings: Settings, *, max_age: int | None) -> dict[str, Any]:
    """Kwargs comunes para `response.set_cookie` del refresh token."""
    return {
        "key": REFRESH_COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.app_env != "local",
        "path": "/",
        "max_age": max_age,
    }
