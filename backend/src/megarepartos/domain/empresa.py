"""Domain de empresa — get/update de la empresa actual (la del JWT)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.models.empresa import Empresa


async def obtener_empresa(session: AsyncSession, *, empresa_id: uuid.UUID) -> Empresa:
    """Devuelve la empresa del JWT o 404."""
    empresa = (
        await session.execute(select(Empresa).where(Empresa.id == empresa_id))
    ).scalar_one_or_none()
    if empresa is None:
        raise ApiError(ErrorCode.RECURSO_NO_ENCONTRADO, "Empresa no encontrada.")
    return empresa


async def actualizar_empresa(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    cambios: dict[str, Any],
) -> Empresa:
    """REQ-EMP-007: admin actualiza datos de su propia empresa."""
    empresa = await obtener_empresa(session, empresa_id=empresa_id)

    if "nombre" in cambios and cambios["nombre"] is not None:
        cambios["nombre"] = cambios["nombre"].strip()

    diff: dict[str, dict[str, Any]] = {}
    for campo, nuevo in cambios.items():
        anterior = getattr(empresa, campo)
        if anterior != nuevo:
            diff[campo] = {"de": anterior, "a": nuevo}
            setattr(empresa, campo, nuevo)

    if not diff:
        return empresa

    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="empresa",
        accion="modificada",
    ) as ev:
        ev.entidad_id = empresa.id
        ev.detalles["diff"] = diff

    return empresa
