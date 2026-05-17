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


@dataclass(slots=True)
class PendienteRow:
    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_telefono: str
    fecha_link: datetime


@dataclass(slots=True)
class HistorialEvento:
    """Una entrada del historial de un cliente (respuesta o link generado)."""

    evento_id: uuid.UUID
    accion: str  # "respondio_link" | "link_generado"
    fecha: datetime
    detalles: dict[str, Any] = field(default_factory=dict)


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


async def listar_pendientes(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    desde_dias: int = 7,
) -> list[PendienteRow]:
    """REQ-PED-006 (SPEC 6.9): clientes con `link_generado` en los últimos
    `desde_dias` días y sin `respondio_link` posterior.

    Para cada cliente se queda con la fecha del último link generado.
    """
    cutoff = datetime.now(UTC) - timedelta(days=desde_dias)

    # Latest link_generado per cliente, in window.
    latest_link = (
        select(
            EventoDominio.entidad_id.label("cliente_id"),
            func.max(EventoDominio.fecha).label("fecha_link"),
        )
        .where(
            EventoDominio.empresa_id == empresa_id,
            EventoDominio.entidad_tipo == "cliente",
            EventoDominio.accion == "link_generado",
            EventoDominio.fecha >= cutoff,
        )
        .group_by(EventoDominio.entidad_id)
        .subquery()
    )

    # Latest respondio_link per cliente.
    latest_resp = (
        select(
            EventoDominio.entidad_id.label("cliente_id"),
            func.max(EventoDominio.fecha).label("fecha_resp"),
        )
        .where(
            EventoDominio.empresa_id == empresa_id,
            EventoDominio.entidad_tipo == "cliente",
            EventoDominio.accion == "respondio_link",
        )
        .group_by(EventoDominio.entidad_id)
        .subquery()
    )

    stmt = (
        select(
            latest_link.c.cliente_id,
            Cliente.nombre_completo,
            Cliente.telefono,
            latest_link.c.fecha_link,
        )
        .join(Cliente, Cliente.id == latest_link.c.cliente_id)
        .outerjoin(latest_resp, latest_resp.c.cliente_id == latest_link.c.cliente_id)
        .where(
            Cliente.activo.is_(True),
            (latest_resp.c.fecha_resp.is_(None))
            | (latest_resp.c.fecha_resp < latest_link.c.fecha_link),
        )
        .order_by(latest_link.c.fecha_link.desc())
    )

    rows = (await session.execute(stmt)).all()
    return [
        PendienteRow(
            cliente_id=r[0],
            cliente_nombre=r[1],
            cliente_telefono=r[2],
            fecha_link=r[3],
        )
        for r in rows
    ]


async def historial_cliente(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    cliente_id: uuid.UUID,
    limit: int = 20,
) -> list[HistorialEvento]:
    """REQ-PED-007: lista las últimas N interacciones (link_generado y
    respondio_link) de un cliente, orden fecha desc.
    """
    stmt = (
        select(
            EventoDominio.id,
            EventoDominio.accion,
            EventoDominio.fecha,
            EventoDominio.detalles_jsonb,
        )
        .where(
            EventoDominio.empresa_id == empresa_id,
            EventoDominio.entidad_tipo == "cliente",
            EventoDominio.entidad_id == cliente_id,
            EventoDominio.accion.in_(["link_generado", "respondio_link"]),
        )
        .order_by(EventoDominio.fecha.desc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()
    return [
        HistorialEvento(
            evento_id=r[0],
            accion=r[1],
            fecha=r[2],
            detalles=r[3] or {},
        )
        for r in rows
    ]
