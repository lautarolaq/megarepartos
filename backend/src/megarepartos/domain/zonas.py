"""Domain de zonas: CRUD + audit."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.domain._repository import get_or_404, list_by_empresa
from megarepartos.models.zona import Zona


async def listar_zonas(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    activo: bool | None = None,
) -> list[Zona]:
    """REQ-ZONA-001/002."""
    filters = []
    if activo is not None:
        filters.append(Zona.activo.is_(activo))
    return await list_by_empresa(
        session,
        Zona,
        empresa_id=empresa_id,
        filters=filters,
        order_by=[Zona.nombre.asc()],
        limit=200,
    )


async def obtener_zona(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    zona_id: uuid.UUID,
) -> Zona:
    """REQ-ZONA-003."""
    return await get_or_404(session, Zona, id_=zona_id, empresa_id=empresa_id)


async def crear_zona(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    nombre: str,
    dia_visita: str | None,
    camioneta_asignada: str | None,
    color_display: str | None,
) -> Zona:
    """REQ-ZONA-004."""
    zona = Zona(
        empresa_id=empresa_id,
        nombre=nombre,
        dia_visita=dia_visita,
        camioneta_asignada=camioneta_asignada,
        color_display=color_display,
        activo=True,
    )
    session.add(zona)
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="zona",
        accion="creada",
    ) as ev:
        ev.entidad_id = zona.id
        ev.detalles["nombre"] = nombre
        if dia_visita:
            ev.detalles["dia_visita"] = dia_visita

    return zona


async def actualizar_zona(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    zona_id: uuid.UUID,
    cambios: dict[str, Any],
) -> Zona:
    """REQ-ZONA-005."""
    zona = await obtener_zona(session, empresa_id=empresa_id, zona_id=zona_id)
    diff: dict[str, dict[str, Any]] = {}
    for campo, nuevo in cambios.items():
        anterior = getattr(zona, campo)
        if anterior != nuevo:
            diff[campo] = {"de": _serializable(anterior), "a": _serializable(nuevo)}
            setattr(zona, campo, nuevo)

    if not diff:
        return zona

    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="zona",
        accion="modificada",
    ) as ev:
        ev.entidad_id = zona.id
        ev.detalles["diff"] = diff

    return zona


async def desactivar_zona(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    zona_id: uuid.UUID,
) -> None:
    """REQ-ZONA-006."""
    zona = await obtener_zona(session, empresa_id=empresa_id, zona_id=zona_id)
    if not zona.activo:
        return

    zona.activo = False
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="zona",
        accion="desactivada",
    ) as ev:
        ev.entidad_id = zona.id


def _serializable(v: Any) -> Any:
    if isinstance(v, uuid.UUID):
        return str(v)
    return v
