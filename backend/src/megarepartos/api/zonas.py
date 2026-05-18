"""Router `/api/zonas/*`. Mismo patrón que productos y envases."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.zonas import (
    actualizar_zona,
    crear_zona,
    desactivar_zona,
    listar_zonas,
    obtener_zona,
)
from megarepartos.infra.auth import (
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
)
from megarepartos.schemas.zona import (
    ZonaCreate,
    ZonaListOut,
    ZonaOut,
    ZonaUpdate,
)

router = APIRouter(prefix="/api/zonas", tags=["zonas"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]
AdminDep = Annotated[TokenClaims, Depends(require_rol("admin"))]


@router.get("", response_model=ZonaListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    activo: Annotated[bool | None, Query()] = None,
) -> ZonaListOut:
    zonas = await listar_zonas(session, empresa_id=claims.empresa_id, activo=activo)
    return ZonaListOut(items=[ZonaOut.model_validate(z) for z in zonas])


@router.get("/{zona_id}", response_model=ZonaOut)
async def detalle(
    zona_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> ZonaOut:
    zona = await obtener_zona(session, empresa_id=claims.empresa_id, zona_id=zona_id)
    return ZonaOut.model_validate(zona)


@router.post("", response_model=ZonaOut, status_code=201)
async def crear(
    payload: ZonaCreate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ZonaOut:
    zona = await crear_zona(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        nombre=payload.nombre,
        dia_visita=payload.dia_visita,
        camioneta_asignada=payload.camioneta_asignada,
        color_display=payload.color_display,
        broadcast_list_name=payload.broadcast_list_name,
    )
    return ZonaOut.model_validate(zona)


@router.patch("/{zona_id}", response_model=ZonaOut)
async def actualizar(
    zona_id: uuid.UUID,
    payload: ZonaUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ZonaOut:
    cambios = payload.model_dump(exclude_unset=True)
    zona = await actualizar_zona(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        zona_id=zona_id,
        cambios=cambios,
    )
    return ZonaOut.model_validate(zona)


@router.delete("/{zona_id}", status_code=204)
async def borrar(
    zona_id: uuid.UUID,
    admin_claims: AdminDep,
    session: SessionDep,
) -> Response:
    await desactivar_zona(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        zona_id=zona_id,
    )
    return Response(status_code=204)
