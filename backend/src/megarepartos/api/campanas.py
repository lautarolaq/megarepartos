"""Router `/api/campanas/*` — listado + detalle de campañas de la empresa.

Una campaña agrupa todas las respuestas de un envío (broadcast o bulk
individual). Permite al sodero ver "confirmados de la difusión zona norte
miércoles" como bloque coherente, separado de otras campañas.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.campanas import (
    listar_campanas as domain_listar_campanas,
)
from megarepartos.domain.campanas import (
    obtener_campana_detalle,
)
from megarepartos.infra.auth import TokenClaims, authenticated_session, current_claims
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.schemas.campana import (
    CampanaDetalleOut,
    CampanaListOut,
    CampanaResumenOut,
    RespuestaCampanaOut,
)

router = APIRouter(prefix="/api/campanas", tags=["campanas"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]


@router.get("", response_model=CampanaListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    limit: int = 50,
    offset: int = 0,
) -> CampanaListOut:
    items = await domain_listar_campanas(
        session, empresa_id=claims.empresa_id, limit=limit, offset=offset
    )
    return CampanaListOut(
        items=[
            CampanaResumenOut(
                id=str(c.id),
                nombre=c.nombre,
                tipo_envio=c.tipo_envio,
                zona_id=str(c.zona_id) if c.zona_id else None,
                zona_nombre=c.zona_nombre,
                mensaje=c.mensaje,
                fecha_creacion=c.fecha_creacion,
                n_confirmados=c.n_confirmados,
                n_rechazados=c.n_rechazados,
            )
            for c in items
        ]
    )


@router.get("/{campana_id}", response_model=CampanaDetalleOut)
async def detalle(
    campana_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> CampanaDetalleOut:
    det = await obtener_campana_detalle(
        session, empresa_id=claims.empresa_id, campana_id=campana_id
    )
    if det is None:
        raise ApiError(ErrorCode.RECURSO_NO_ENCONTRADO, "Campaña no encontrada.")

    accion_type = Literal["confirmo", "rechazo"]  # noqa: F841 — usado por Pydantic implícitamente

    return CampanaDetalleOut(
        id=str(det.id),
        nombre=det.nombre,
        tipo_envio=det.tipo_envio,
        zona_id=str(det.zona_id) if det.zona_id else None,
        zona_nombre=det.zona_nombre,
        mensaje=det.mensaje,
        fecha_creacion=det.fecha_creacion,
        respuestas=[
            RespuestaCampanaOut(
                cliente_id=str(r.cliente_id),
                cliente_nombre=r.cliente_nombre,
                cliente_telefono=r.cliente_telefono,
                accion=r.accion,
                fecha=r.fecha,
                productos=r.productos,
            )
            for r in det.respuestas
        ],
    )
