"""Router `/api/empresa/*` — get/update de la empresa actual del JWT."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.empresa import actualizar_empresa, obtener_empresa
from megarepartos.infra.auth import (
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
)
from megarepartos.schemas.empresa import EmpresaOut, EmpresaUpdate

router = APIRouter(prefix="/api/empresa", tags=["empresa"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]
AdminDep = Annotated[TokenClaims, Depends(require_rol("admin"))]


@router.get("/me", response_model=EmpresaOut)
async def me(claims: ClaimsDep, session: SessionDep) -> EmpresaOut:
    """REQ-EMP-008: devuelve la empresa del usuario autenticado."""
    empresa = await obtener_empresa(session, empresa_id=claims.empresa_id)
    return EmpresaOut.model_validate(empresa)


@router.patch("/me", response_model=EmpresaOut)
async def actualizar_me(
    payload: EmpresaUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> EmpresaOut:
    """REQ-EMP-007: admin actualiza datos de su empresa."""
    cambios = payload.model_dump(exclude_unset=True)
    empresa = await actualizar_empresa(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        cambios=cambios,
    )
    return EmpresaOut.model_validate(empresa)
