"""Router `/api/pedidos/*` — listado de respuestas de clientes (motor 2).

Los pedidos son un view sobre `evento_dominio` filtrado por
`accion="respondio_link"`. No hay tabla propia: cuando un cliente responde
desde el link público, se persiste como `EventoDominio` (ver `api/publico.py`).

RLS aplica vía `authenticated_session` (filtra por `empresa_id`), pero
mantenemos el filtro explícito por defensa en profundidad.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.infra.auth import TokenClaims, authenticated_session, current_claims
from megarepartos.models.cliente import Cliente
from megarepartos.models.evento import EventoDominio
from megarepartos.schemas.pedido import PedidoListOut, PedidoOut, ProductoPedido

router = APIRouter(prefix="/api/pedidos", tags=["pedidos"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]


@router.get("", response_model=PedidoListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PedidoListOut:
    """REQ-LINK-007: lista respuestas de clientes ordenadas por fecha desc."""
    base = (
        select(
            EventoDominio.id.label("evento_id"),
            EventoDominio.entidad_id.label("cliente_id"),
            EventoDominio.detalles_jsonb.label("detalles"),
            EventoDominio.fecha.label("fecha"),
            Cliente.nombre_completo.label("cliente_nombre"),
            Cliente.telefono.label("cliente_telefono"),
        )
        .join(Cliente, Cliente.id == EventoDominio.entidad_id)
        .where(
            EventoDominio.empresa_id == claims.empresa_id,
            EventoDominio.entidad_tipo == "cliente",
            EventoDominio.accion == "respondio_link",
        )
    )

    total = (
        await session.execute(
            select(func.count())
            .select_from(EventoDominio)
            .join(Cliente, Cliente.id == EventoDominio.entidad_id)
            .where(
                EventoDominio.empresa_id == claims.empresa_id,
                EventoDominio.entidad_tipo == "cliente",
                EventoDominio.accion == "respondio_link",
            )
        )
    ).scalar_one()

    rows = (
        await session.execute(
            base.order_by(EventoDominio.fecha.desc()).limit(limit).offset(offset)
        )
    ).all()

    items: list[PedidoOut] = []
    for row in rows:
        detalles = row.detalles or {}
        productos_raw = detalles.get("productos", []) or []
        productos = [
            ProductoPedido(
                producto_id=str(p.get("producto_id", "")),
                nombre=str(p.get("nombre", "")),
                cantidad_llenos=int(p.get("cantidad_llenos", 0)),
                cantidad_vacios=int(p.get("cantidad_vacios", 0)),
                es_retornable=bool(p.get("es_retornable", False)),
            )
            for p in productos_raw
        ]
        items.append(
            PedidoOut(
                evento_id=row.evento_id,
                cliente_id=row.cliente_id,
                cliente_nombre=row.cliente_nombre,
                cliente_telefono=row.cliente_telefono,
                accion=str(detalles.get("accion", "")),
                productos=productos,
                observacion=detalles.get("observacion"),
                fecha=row.fecha,
            )
        )

    return PedidoListOut(items=items, total=total, limit=limit, offset=offset)
