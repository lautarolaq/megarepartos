"""Domain de usuarios (gestión interna)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.domain._repository import get_or_404, list_by_empresa
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.models.usuario import Usuario


async def listar_usuarios(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    activo: bool | None = None,
) -> list[Usuario]:
    """REQ-USR-001/002."""
    filters = []
    if activo is not None:
        filters.append(Usuario.activo.is_(activo))
    return await list_by_empresa(
        session,
        Usuario,
        empresa_id=empresa_id,
        filters=filters,
        order_by=[Usuario.nombre.asc()],
        limit=200,
    )


async def obtener_usuario(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> Usuario:
    """REQ-USR-003."""
    return await get_or_404(session, Usuario, id_=usuario_id, empresa_id=empresa_id)


async def actualizar_usuario(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    actor_id: uuid.UUID,
    usuario_id: uuid.UUID,
    cambios: dict[str, Any],
) -> Usuario:
    """REQ-USR-004/008/009: cambia rol/activo. Admin no puede auto-desactivarse."""
    usuario = await obtener_usuario(session, empresa_id=empresa_id, usuario_id=usuario_id)

    # REQ-USR-008: bloquear auto-desactivación.
    if "activo" in cambios and cambios["activo"] is False and usuario.id == actor_id:
        raise ApiError(
            ErrorCode.CONFLICTO_ESTADO,
            "No podés desactivarte a vos mismo.",
        )

    diff: dict[str, dict[str, Any]] = {}
    for campo, nuevo in cambios.items():
        anterior = getattr(usuario, campo)
        if anterior != nuevo:
            diff[campo] = {"de": anterior, "a": nuevo}
            setattr(usuario, campo, nuevo)

    if not diff:
        return usuario

    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=actor_id,
        entidad_tipo="usuario",
        accion="modificado",
    ) as ev:
        ev.entidad_id = usuario.id
        ev.detalles["diff"] = diff

    return usuario


async def desactivar_usuario(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    actor_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> None:
    """REQ-USR-007/008."""
    if usuario_id == actor_id:
        raise ApiError(
            ErrorCode.CONFLICTO_ESTADO,
            "No podés desactivarte a vos mismo.",
        )

    usuario = await obtener_usuario(session, empresa_id=empresa_id, usuario_id=usuario_id)
    if not usuario.activo:
        return

    usuario.activo = False
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=actor_id,
        entidad_tipo="usuario",
        accion="desactivado",
    ) as ev:
        ev.entidad_id = usuario.id
