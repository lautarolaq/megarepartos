"""Router `/api/pedidos/*` — listado de respuestas de clientes (motor 2).

Los pedidos son un view sobre `evento_dominio` filtrado por
`accion="respondio_link"`. La query vive en `domain.pedidos` (CLAUDE.md
Backend #6: api/ no importa models/).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.pedidos import listar_pedidos, stats_pedidos
from megarepartos.infra.auth import TokenClaims, authenticated_session, current_claims
from megarepartos.schemas.pedido import PedidoListOut, PedidoOut, PedidoStatsOut, ProductoPedido

router = APIRouter(prefix="/api/pedidos", tags=["pedidos"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]


@router.get("", response_model=PedidoListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    accion: Annotated[str | None, Query(description="'confirmo' o 'rechazo'")] = None,
    desde_dias: Annotated[
        int | None,
        Query(ge=1, le=365, description="Sólo pedidos de los últimos N días."),
    ] = None,
) -> PedidoListOut:
    """REQ-LINK-007: lista respuestas de clientes ordenadas por fecha desc."""
    rows, total = await listar_pedidos(
        session,
        empresa_id=claims.empresa_id,
        limit=limit,
        offset=offset,
        accion=accion,
        desde_dias=desde_dias,
    )

    items: list[PedidoOut] = []
    for row in rows:
        productos_raw = row.detalles.get("productos", []) or []
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
                accion=str(row.detalles.get("accion", "")),
                productos=productos,
                observacion=row.detalles.get("observacion"),
                fecha=row.fecha,
            )
        )

    return PedidoListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/stats", response_model=PedidoStatsOut)
async def stats(claims: ClaimsDep, session: SessionDep) -> PedidoStatsOut:
    """REQ-LINK-007: resumen del día/semana para el dashboard."""
    s = await stats_pedidos(session, empresa_id=claims.empresa_id)
    return PedidoStatsOut(
        pedidos_hoy=s.pedidos_hoy,
        confirmados_hoy=s.confirmados_hoy,
        pedidos_semana=s.pedidos_semana,
        clientes_activos=s.clientes_activos,
    )
