"""Router `/api/clientes/*` — CRUD con búsqueda y paginación."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.clientes import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    actualizar_cliente,
    crear_cliente,
    desactivar_cliente,
    listar_clientes,
    obtener_cliente,
)
from megarepartos.infra.auth import (
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
)
from megarepartos.schemas.cliente import (
    ClienteCreate,
    ClienteListOut,
    ClienteOut,
    ClienteUpdate,
)

router = APIRouter(prefix="/api/clientes", tags=["clientes"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]
AdminDep = Annotated[TokenClaims, Depends(require_rol("admin"))]


@router.get("", response_model=ClienteListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    q: Annotated[str | None, Query()] = None,
    modalidad: Annotated[str | None, Query()] = None,
    zona_id: Annotated[uuid.UUID | None, Query()] = None,
    activo: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ClienteListOut:
    items, total = await listar_clientes(
        session,
        empresa_id=claims.empresa_id,
        q=q,
        modalidad=modalidad,
        zona_id=zona_id,
        activo=activo,
        limit=limit,
        offset=offset,
    )
    return ClienteListOut(
        items=[ClienteOut.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{cliente_id}", response_model=ClienteOut)
async def detalle(
    cliente_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> ClienteOut:
    cliente = await obtener_cliente(session, empresa_id=claims.empresa_id, cliente_id=cliente_id)
    return ClienteOut.model_validate(cliente)


@router.post("", response_model=ClienteOut, status_code=201)
async def crear(
    payload: ClienteCreate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ClienteOut:
    cliente = await crear_cliente(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        nombre_completo=payload.nombre_completo,
        telefono=payload.telefono,
        email=payload.email,
        direccion=payload.direccion,
        zona_id=payload.zona_id,
        modalidad=payload.modalidad,
        frecuencia=payload.frecuencia,
        observaciones_permanentes=payload.observaciones_permanentes,
        condicion_pago=payload.condicion_pago,
    )
    return ClienteOut.model_validate(cliente)


@router.patch("/{cliente_id}", response_model=ClienteOut)
async def actualizar(
    cliente_id: uuid.UUID,
    payload: ClienteUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ClienteOut:
    cambios = payload.model_dump(exclude_unset=True)
    cliente = await actualizar_cliente(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        cliente_id=cliente_id,
        cambios=cambios,
    )
    return ClienteOut.model_validate(cliente)


@router.delete("/{cliente_id}", status_code=204)
async def borrar(
    cliente_id: uuid.UUID,
    admin_claims: AdminDep,
    session: SessionDep,
) -> Response:
    await desactivar_cliente(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        cliente_id=cliente_id,
    )
    return Response(status_code=204)
