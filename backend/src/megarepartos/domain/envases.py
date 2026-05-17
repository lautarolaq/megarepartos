"""Domain de envases: CRUD + audit."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.domain._repository import get_or_404, list_by_empresa
from megarepartos.models.producto import Envase


async def listar_envases(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    activo: bool | None = None,
) -> list[Envase]:
    """REQ-ENV-001/002."""
    filters = []
    if activo is not None:
        filters.append(Envase.activo.is_(activo))
    return await list_by_empresa(
        session,
        Envase,
        empresa_id=empresa_id,
        filters=filters,
        order_by=[Envase.nombre.asc()],
        limit=200,
    )


async def obtener_envase(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    envase_id: uuid.UUID,
) -> Envase:
    """REQ-ENV-003."""
    return await get_or_404(session, Envase, id_=envase_id, empresa_id=empresa_id)


async def crear_envase(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    nombre: str,
    valor_referencial: Decimal | None,
) -> Envase:
    """REQ-ENV-004."""
    envase = Envase(
        empresa_id=empresa_id,
        nombre=nombre,
        valor_referencial=valor_referencial,
        activo=True,
    )
    session.add(envase)
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="envase",
        accion="creado",
    ) as ev:
        ev.entidad_id = envase.id
        ev.detalles["nombre"] = nombre

    return envase


async def actualizar_envase(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    envase_id: uuid.UUID,
    cambios: dict[str, Any],
) -> Envase:
    """REQ-ENV-005."""
    envase = await obtener_envase(session, empresa_id=empresa_id, envase_id=envase_id)
    diff: dict[str, dict[str, Any]] = {}
    for campo, nuevo in cambios.items():
        anterior = getattr(envase, campo)
        if anterior != nuevo:
            diff[campo] = {"de": _serializable(anterior), "a": _serializable(nuevo)}
            setattr(envase, campo, nuevo)

    if not diff:
        return envase

    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="envase",
        accion="modificado",
    ) as ev:
        ev.entidad_id = envase.id
        ev.detalles["diff"] = diff

    return envase


async def desactivar_envase(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    envase_id: uuid.UUID,
) -> None:
    """REQ-ENV-006."""
    envase = await obtener_envase(session, empresa_id=empresa_id, envase_id=envase_id)
    if not envase.activo:
        return

    envase.activo = False
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="envase",
        accion="desactivado",
    ) as ev:
        ev.entidad_id = envase.id


def _serializable(v: Any) -> Any:
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, Decimal):
        return str(v)
    return v
