"""Router `/api/envases/*`. Mismo patrón que productos."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.envases import (
    actualizar_envase,
    crear_envase,
    desactivar_envase,
    listar_envases,
    obtener_envase,
)
from megarepartos.infra.auth import (
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
)
from megarepartos.schemas.envase import (
    EnvaseCreate,
    EnvaseListOut,
    EnvaseOut,
    EnvaseUpdate,
)

router = APIRouter(prefix="/api/envases", tags=["envases"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]
AdminDep = Annotated[TokenClaims, Depends(require_rol("admin"))]


@router.get("", response_model=EnvaseListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    activo: Annotated[bool | None, Query()] = None,
) -> EnvaseListOut:
    envases = await listar_envases(session, empresa_id=claims.empresa_id, activo=activo)
    return EnvaseListOut(items=[EnvaseOut.model_validate(e) for e in envases])


@router.get("/{envase_id}", response_model=EnvaseOut)
async def detalle(
    envase_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> EnvaseOut:
    envase = await obtener_envase(session, empresa_id=claims.empresa_id, envase_id=envase_id)
    return EnvaseOut.model_validate(envase)


@router.post("", response_model=EnvaseOut, status_code=201)
async def crear(
    payload: EnvaseCreate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> EnvaseOut:
    envase = await crear_envase(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        nombre=payload.nombre,
        valor_referencial=payload.valor_referencial,
    )
    return EnvaseOut.model_validate(envase)


@router.patch("/{envase_id}", response_model=EnvaseOut)
async def actualizar(
    envase_id: uuid.UUID,
    payload: EnvaseUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> EnvaseOut:
    cambios = payload.model_dump(exclude_unset=True)
    envase = await actualizar_envase(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        envase_id=envase_id,
        cambios=cambios,
    )
    return EnvaseOut.model_validate(envase)


@router.delete("/{envase_id}", status_code=204)
async def borrar(
    envase_id: uuid.UUID,
    admin_claims: AdminDep,
    session: SessionDep,
) -> Response:
    await desactivar_envase(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        envase_id=envase_id,
    )
    return Response(status_code=204)
