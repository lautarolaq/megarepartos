"""Router `/api/auth/*`.

Sólo importa de `domain/`, `schemas/`, `infra/auth`, `infra/errors`, `infra/db`,
`config`. NUNCA de `models/` (regla CLAUDE.md Backend #6).
"""

from __future__ import annotations

import urllib.parse
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.domain.auth import login_or_create_user, obtener_contexto_actual
from megarepartos.infra import auth as auth_infra  # acceso por módulo para monkey-patch en tests
from megarepartos.infra.auth import (
    REFRESH_COOKIE_NAME,
    TokenClaims,
    current_claims,
    decode_token,
    issue_access_token,
    issue_refresh_token,
    refresh_cookie_kwargs,
    sign_state,
    verify_state,
)
from megarepartos.infra.db import get_session
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.schemas.auth import (
    AccessTokenOut,
    EmpresaOut,
    GoogleAuthUrl,
    MeOut,
    UsuarioOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DEFAULT_SCOPES = ["openid", "email", "profile"]

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/google/url", response_model=GoogleAuthUrl)
async def google_auth_url(settings: SettingsDep) -> GoogleAuthUrl:
    """REQ-AUTH-001: URL de autorización de Google con `state` firmado."""
    if not settings.google_oauth_client_id:
        raise ApiError(
            ErrorCode.EXTERNO_FALLO,
            "GOOGLE_OAUTH_CLIENT_ID no configurado en el servidor.",
        )
    state = sign_state(settings)
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_url,
        "response_type": "code",
        "scope": " ".join(GOOGLE_DEFAULT_SCOPES),
        "state": state,
        "access_type": "offline",
        # No `prompt=consent`: Google decide (consent solo la primera vez).
        # `select_account` permite cambiar de cuenta sin re-consentir.
        "prompt": "select_account",
    }
    return GoogleAuthUrl(url=f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")


async def _exchange_code_for_id_token(
    *,
    code: str,
    settings: Settings,
) -> str:
    """Intercambia `code` por `id_token` contra Google. Devuelve el id_token raw."""
    if not (settings.google_oauth_client_id and settings.google_oauth_client_secret):
        raise ApiError(ErrorCode.EXTERNO_FALLO, "OAuth credentials no configuradas en el servidor.")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_url,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise ApiError(
            ErrorCode.AUTH_INVALID,
            "Google rechazó el code.",
            details={"google_status": resp.status_code},
        )
    payload = resp.json()
    id_token_str = payload.get("id_token")
    if not id_token_str:
        raise ApiError(ErrorCode.AUTH_INVALID, "Respuesta de Google sin id_token.")
    return id_token_str


def _frontend_callback_url(settings: Settings, access_token: str) -> str:
    """URL del frontend a la que redirigimos después del login.

    El access_token va en el fragmento (#) para que NO se mande al servidor en
    las requests siguientes ni quede en logs de proxy.
    """
    base = (
        "http://localhost:5173/auth/callback" if settings.app_env == "local" else "/auth/callback"
    )
    return f"{base}#access_token={urllib.parse.quote(access_token)}"


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    session: SessionDep,
    settings: SettingsDep,
) -> Response:
    """REQ-AUTH-002 / 003: maneja el redirect de Google.

    Valida state, intercambia code → id_token, verifica id_token, ejecuta
    `login_or_create_user`, setea cookie de refresh y redirige al frontend.
    """
    verify_state(settings, state)

    id_token_str = await _exchange_code_for_id_token(code=code, settings=settings)
    profile = auth_infra.verify_google_id_token(id_token_str)

    empresa, usuario = await login_or_create_user(session, profile)
    await session.commit()

    access_token, _ = issue_access_token(
        settings=settings,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
        rol=usuario.rol,
    )
    refresh_token, refresh_ttl = issue_refresh_token(
        settings=settings,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
        rol=usuario.rol,
    )

    response = RedirectResponse(_frontend_callback_url(settings, access_token))
    response.set_cookie(
        value=refresh_token,
        **refresh_cookie_kwargs(settings, max_age=refresh_ttl),
    )
    return response


@router.post("/refresh", response_model=AccessTokenOut)
async def refresh(
    request: Request,
    settings: SettingsDep,
) -> AccessTokenOut:
    """REQ-AUTH-004 / 005 / 006: emite nuevo access usando el refresh en cookie."""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise ApiError(ErrorCode.AUTH_REQUIRED, "Falta cookie de refresh.")

    claims = decode_token(refresh_token, settings=settings, expected_type="refresh")

    access_token, expires_in = issue_access_token(
        settings=settings,
        usuario_id=claims.sub,
        empresa_id=claims.empresa_id,
        rol=claims.rol,
    )
    return AccessTokenOut(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=204)
async def logout(response: Response, settings: SettingsDep) -> Response:
    """REQ-AUTH-007: limpia la cookie de refresh. Idempotente."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        secure=settings.app_env != "local",
        samesite="lax",
        httponly=True,
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=MeOut)
async def me(
    claims: Annotated[TokenClaims, Depends(current_claims)],
    session: SessionDep,
) -> MeOut:
    """REQ-AUTH-008 / 009 / 010: devuelve usuario + empresa del token actual."""
    empresa, usuario = await obtener_contexto_actual(
        session,
        usuario_id=claims.sub,
        empresa_id=claims.empresa_id,
    )
    return MeOut(
        usuario=UsuarioOut.model_validate(usuario),
        empresa=EmpresaOut.model_validate(empresa),
    )
