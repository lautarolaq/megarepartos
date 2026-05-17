"""Router `/api/empresa/*` — get/update de la empresa actual del JWT."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.empresa import CONFIG_KEYS, actualizar_empresa, obtener_empresa
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


def _to_out(empresa: object) -> EmpresaOut:
    """Construye EmpresaOut combinando columnas + config_jsonb."""
    config = getattr(empresa, "config_jsonb", None) or {}
    data = {
        "id": empresa.id,  # type: ignore[attr-defined]
        "nombre": empresa.nombre,  # type: ignore[attr-defined]
        "tipo_negocio": empresa.tipo_negocio,  # type: ignore[attr-defined]
        "estado_suscripcion": empresa.estado_suscripcion,  # type: ignore[attr-defined]
        "direccion_deposito": empresa.direccion_deposito,  # type: ignore[attr-defined]
        "timezone": empresa.timezone,  # type: ignore[attr-defined]
    }
    for key in CONFIG_KEYS:
        data[key] = config.get(key)
    return EmpresaOut(**data)


@router.get("/me", response_model=EmpresaOut)
async def me(claims: ClaimsDep, session: SessionDep) -> EmpresaOut:
    """REQ-EMP-008: devuelve la empresa del usuario autenticado."""
    empresa = await obtener_empresa(session, empresa_id=claims.empresa_id)
    return _to_out(empresa)


@router.patch("/me", response_model=EmpresaOut)
async def actualizar_me(
    payload: EmpresaUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> EmpresaOut:
    """REQ-EMP-007/009: admin actualiza datos de su empresa."""
    cambios = payload.model_dump(exclude_unset=True)
    empresa = await actualizar_empresa(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        cambios=cambios,
    )
    return _to_out(empresa)
