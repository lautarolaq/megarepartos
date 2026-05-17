"""Router `/api/productos/*` — CRUD del catálogo de productos.

Cada endpoint depende de `authenticated_session` (TASK-001/003) y, donde
corresponda, `require_rol("admin")` (TASK-007). Toda escritura genera
EventoDominio vía `event_recorder` (TASK-005). Aislamiento multi-tenant
garantizado por RLS (TASK-003) + filtros explícitos en domain (TASK-004).

NO importa de `models/` (regla CLAUDE.md Backend #6).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.productos import (
    actualizar_producto,
    crear_producto,
    desactivar_producto,
    listar_productos,
    obtener_producto,
)
from megarepartos.infra.auth import (
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
)
from megarepartos.schemas.producto import (
    ProductoCreate,
    ProductoListOut,
    ProductoOut,
    ProductoUpdate,
)

router = APIRouter(prefix="/api/productos", tags=["productos"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]
AdminDep = Annotated[TokenClaims, Depends(require_rol("admin"))]


@router.get("", response_model=ProductoListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    activo: Annotated[bool | None, Query()] = None,
) -> ProductoListOut:
    """REQ-PROD-001/002: listado de productos, ordenado, con filtro opcional `activo`."""
    productos = await listar_productos(session, empresa_id=claims.empresa_id, activo=activo)
    return ProductoListOut(items=[ProductoOut.model_validate(p) for p in productos])


@router.get("/{producto_id}", response_model=ProductoOut)
async def detalle(
    producto_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> ProductoOut:
    """REQ-PROD-003: 404 si no pertenece a la empresa."""
    producto = await obtener_producto(
        session, empresa_id=claims.empresa_id, producto_id=producto_id
    )
    return ProductoOut.model_validate(producto)


@router.post("", response_model=ProductoOut, status_code=201)
async def crear(
    payload: ProductoCreate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ProductoOut:
    """REQ-PROD-004/005/006/012: solo admin, valida envase si está, audita."""
    producto = await crear_producto(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        precio_unitario_default=payload.precio_unitario_default,
        es_retornable=payload.es_retornable,
        envase_id=payload.envase_id,
        orden_display=payload.orden_display,
    )
    return ProductoOut.model_validate(producto)


@router.patch("/{producto_id}", response_model=ProductoOut)
async def actualizar(
    producto_id: uuid.UUID,
    payload: ProductoUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ProductoOut:
    """REQ-PROD-007/008: PATCH parcial. 404 si ajeno."""
    cambios = payload.model_dump(exclude_unset=True)
    producto = await actualizar_producto(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        producto_id=producto_id,
        cambios=cambios,
    )
    return ProductoOut.model_validate(producto)


@router.delete("/{producto_id}", status_code=204)
async def borrar(
    producto_id: uuid.UUID,
    admin_claims: AdminDep,
    session: SessionDep,
) -> Response:
    """REQ-PROD-009/010: soft delete idempotente."""
    await desactivar_producto(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        producto_id=producto_id,
    )
    return Response(status_code=204)
