"""Router `/api/usuarios/*` — gestión interna de usuarios de la empresa."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.usuarios import (
    actualizar_usuario,
    desactivar_usuario,
    listar_usuarios,
    obtener_usuario,
)
from megarepartos.infra.auth import (
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
)
from megarepartos.schemas.usuario import UsuarioListOut, UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]
AdminDep = Annotated[TokenClaims, Depends(require_rol("admin"))]


@router.get("", response_model=UsuarioListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    activo: Annotated[bool | None, Query()] = None,
) -> UsuarioListOut:
    usuarios = await listar_usuarios(session, empresa_id=claims.empresa_id, activo=activo)
    return UsuarioListOut(items=[UsuarioOut.model_validate(u) for u in usuarios])


@router.get("/{usuario_id}", response_model=UsuarioOut)
async def detalle(
    usuario_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> UsuarioOut:
    usuario = await obtener_usuario(session, empresa_id=claims.empresa_id, usuario_id=usuario_id)
    return UsuarioOut.model_validate(usuario)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
async def actualizar(
    usuario_id: uuid.UUID,
    payload: UsuarioUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> UsuarioOut:
    cambios = payload.model_dump(exclude_unset=True)
    usuario = await actualizar_usuario(
        session,
        empresa_id=admin_claims.empresa_id,
        actor_id=admin_claims.sub,
        usuario_id=usuario_id,
        cambios=cambios,
    )
    return UsuarioOut.model_validate(usuario)


@router.delete("/{usuario_id}", status_code=204)
async def borrar(
    usuario_id: uuid.UUID,
    admin_claims: AdminDep,
    session: SessionDep,
) -> Response:
    await desactivar_usuario(
        session,
        empresa_id=admin_claims.empresa_id,
        actor_id=admin_claims.sub,
        usuario_id=usuario_id,
    )
    return Response(status_code=204)
