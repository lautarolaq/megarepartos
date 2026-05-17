"""Router `/api/pedidos/*` — listado de respuestas de clientes (motor 2).

Los pedidos son un view sobre `evento_dominio` filtrado por
`accion="respondio_link"`. La query vive en `domain.pedidos` (CLAUDE.md
Backend #6: api/ no importa models/).
"""

from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain.pedidos import listar_pedidos, listar_pendientes, stats_pedidos
from megarepartos.infra.auth import TokenClaims, authenticated_session, current_claims
from megarepartos.schemas.pedido import (
    PedidoListOut,
    PedidoOut,
    PedidoStatsOut,
    PendienteOut,
    PendientesListOut,
    ProductoPedido,
)

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
    q: Annotated[str | None, Query(description="Buscar por nombre o teléfono del cliente.")] = None,
) -> PedidoListOut:
    """REQ-LINK-007: lista respuestas de clientes ordenadas por fecha desc."""
    rows, total = await listar_pedidos(
        session,
        empresa_id=claims.empresa_id,
        limit=limit,
        offset=offset,
        accion=accion,
        desde_dias=desde_dias,
        q=q,
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


@router.get("/export.csv")
async def export_csv(
    claims: ClaimsDep,
    session: SessionDep,
    accion: Annotated[str | None, Query(description="'confirmo' o 'rechazo'")] = "confirmo",
    desde_dias: Annotated[int | None, Query(ge=1, le=365)] = 7,
) -> StreamingResponse:
    """REQ-PED-005 (SPEC 6.7): exporta pedidos a CSV para imprimir o pegar en
    la hoja de ruta. Default: confirmados de últimos 7 días.
    """
    rows, _ = await listar_pedidos(
        session,
        empresa_id=claims.empresa_id,
        limit=10_000,
        offset=0,
        accion=accion,
        desde_dias=desde_dias,
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Cliente",
            "Teléfono",
            "Acción",
            "Productos (llenos)",
            "Envases vacíos a recibir",
            "Observación",
            "Fecha",
        ]
    )

    for row in rows:
        productos_raw = row.detalles.get("productos", []) or []
        llenos = [
            f"{int(p.get('cantidad_llenos', 0))} x {p.get('nombre', '')}"
            for p in productos_raw
            if int(p.get("cantidad_llenos", 0)) > 0
        ]
        vacios = [
            f"{int(p.get('cantidad_vacios', 0))} x {p.get('nombre', '')}"
            for p in productos_raw
            if bool(p.get("es_retornable", False)) and int(p.get("cantidad_vacios", 0)) > 0
        ]
        writer.writerow(
            [
                row.cliente_nombre,
                row.cliente_telefono,
                row.detalles.get("accion", ""),
                "; ".join(llenos),
                "; ".join(vacios),
                row.detalles.get("observacion") or "",
                row.fecha.isoformat(),
            ]
        )

    csv_content = buf.getvalue()
    buf.close()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pedidos.csv"'},
    )


@router.get("/pendientes", response_model=PendientesListOut)
async def pendientes(
    claims: ClaimsDep,
    session: SessionDep,
    desde_dias: Annotated[int, Query(ge=1, le=90)] = 7,
) -> PendientesListOut:
    """REQ-PED-006 (SPEC 6.9): clientes con link enviado y sin respuesta posterior."""
    rows = await listar_pendientes(session, empresa_id=claims.empresa_id, desde_dias=desde_dias)
    items = [
        PendienteOut(
            cliente_id=r.cliente_id,
            cliente_nombre=r.cliente_nombre,
            cliente_telefono=r.cliente_telefono,
            fecha_link=r.fecha_link,
        )
        for r in rows
    ]
    return PendientesListOut(items=items, total=len(items))
