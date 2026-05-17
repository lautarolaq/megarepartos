"""Domain de pedidos — view sobre `evento_dominio` filtrado por respuestas de link.

No hay tabla `pedido` propia. Cada respuesta de cliente persiste como
`EventoDominio` con `accion="respondio_link"` (ver `domain.publico`).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.models.cliente import Cliente
from megarepartos.models.evento import EventoDominio


@dataclass(slots=True)
class PedidoRow:
    evento_id: uuid.UUID
    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_telefono: str
    fecha: datetime
    detalles: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PedidoStats:
    pedidos_hoy: int
    confirmados_hoy: int
    pedidos_semana: int
    clientes_activos: int


async def listar_pedidos(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    limit: int,
    offset: int,
    accion: str | None = None,
    desde_dias: int | None = None,
) -> tuple[list[PedidoRow], int]:
    """REQ-LINK-007: lista respuestas paginadas, orden fecha desc.

    Filtros opcionales: `accion` ∈ {"confirmo", "rechazo"} y `desde_dias` rolling.
    """
    base_filters = [
        EventoDominio.empresa_id == empresa_id,
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
        await session.execute(base.order_by(EventoDominio.fecha.desc()).limit(limit).offset(offset))
    ).all()

    items = [
        PedidoRow(
            evento_id=r.evento_id,
            cliente_id=r.cliente_id,
            cliente_nombre=r.cliente_nombre,
            cliente_telefono=r.cliente_telefono,
            fecha=r.fecha,
            detalles=r.detalles or {},
        )
        for r in rows
    ]
    return items, total


async def stats_pedidos(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
) -> PedidoStats:
    """Resumen del día/semana para el dashboard."""
    now = datetime.now(UTC)
    inicio_hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = inicio_hoy - timedelta(days=6)

    base_evento = select(EventoDominio).where(
        EventoDominio.empresa_id == empresa_id,
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
                Cliente.empresa_id == empresa_id,
                Cliente.activo.is_(True),
            )
        )
    ).scalar_one()

    return PedidoStats(
        pedidos_hoy=pedidos_hoy,
        confirmados_hoy=confirmados_hoy,
        pedidos_semana=pedidos_semana,
        clientes_activos=clientes_activos,
    )
