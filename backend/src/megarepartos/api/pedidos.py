"""Router `/api/pedidos/*` — listado de respuestas de clientes (motor 2).

Los pedidos son un view sobre `evento_dominio` filtrado por
`accion="respondio_link"`. No hay tabla propia: cuando un cliente responde
desde el link público, se persiste como `EventoDominio` (ver `api/publico.py`).

RLS aplica vía `authenticated_session` (filtra por `empresa_id`), pero
mantenemos el filtro explícito por defensa en profundidad.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.infra.auth import TokenClaims, authenticated_session, current_claims
from megarepartos.models.cliente import Cliente
from megarepartos.models.evento import EventoDominio
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
    """REQ-LINK-007: lista respuestas de clientes ordenadas por fecha desc.

    Filtros opcionales: `accion` (confirmo/rechazo) y `desde_dias` (rolling).
    """
    base_filters = [
        EventoDominio.empresa_id == claims.empresa_id,
        EventoDominio.entidad_tipo == "cliente",
        EventoDominio.accion == "respondio_link",
    ]
    if accion in ("confirmo", "rechazo"):
        base_filters.append(EventoDominio.detalles_jsonb["accion"].astext == accion)
    if desde_dias is not None:
        cutoff = datetime.now(UTC) - timedelta(days=desde_dias)
        base_filters.append(EventoDominio.fecha >= cutoff)

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
        .where(*base_filters)
    )

    total = (
        await session.execute(
            select(func.count())
            .select_from(EventoDominio)
            .join(Cliente, Cliente.id == EventoDominio.entidad_id)
            .where(*base_filters)
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


@router.get("/stats", response_model=PedidoStatsOut)
async def stats(claims: ClaimsDep, session: SessionDep) -> PedidoStatsOut:
    """Resumen del día/semana para el dashboard."""
    now = datetime.now(UTC)
    inicio_hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # "Esta semana" = últimos 7 días rolling, evita líos con calendarios y husos.
    inicio_semana = inicio_hoy - timedelta(days=6)

    base_evento = select(EventoDominio).where(
        EventoDominio.empresa_id == claims.empresa_id,
        EventoDominio.entidad_tipo == "cliente",
        EventoDominio.accion == "respondio_link",
    )

    pedidos_hoy = (
        await session.execute(
            select(func.count()).select_from(
                base_evento.where(EventoDominio.fecha >= inicio_hoy).subquery()
            )
        )
    ).scalar_one()

    confirmados_hoy = (
        await session.execute(
            select(func.count()).select_from(
                base_evento.where(
                    EventoDominio.fecha >= inicio_hoy,
                    EventoDominio.detalles_jsonb["accion"].astext == "confirmo",
                ).subquery()
            )
        )
    ).scalar_one()

    pedidos_semana = (
        await session.execute(
            select(func.count()).select_from(
                base_evento.where(EventoDominio.fecha >= inicio_semana).subquery()
            )
        )
    ).scalar_one()

    clientes_activos = (
        await session.execute(
            select(func.count(Cliente.id)).where(
                Cliente.empresa_id == claims.empresa_id,
                Cliente.activo.is_(True),
            )
        )
    ).scalar_one()

    return PedidoStatsOut(
        pedidos_hoy=pedidos_hoy,
        confirmados_hoy=confirmados_hoy,
        pedidos_semana=pedidos_semana,
        clientes_activos=clientes_activos,
    )
