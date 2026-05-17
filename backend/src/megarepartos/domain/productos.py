"""Domain de productos: CRUD + audit + validación FK envase."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.domain._repository import (
    exists_in_empresa,
    get_or_404,
    list_by_empresa,
)
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.models.producto import Envase, Producto


async def listar_productos(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    activo: bool | None = None,
) -> list[Producto]:
    """REQ-PROD-001/002: lista productos de la empresa, ordenados, con filtro
    opcional por `activo`.
    """
    filters = []
    if activo is not None:
        filters.append(Producto.activo.is_(activo))
    return await list_by_empresa(
        session,
        Producto,
        empresa_id=empresa_id,
        filters=filters,
        order_by=[Producto.orden_display.asc(), Producto.nombre.asc()],
        limit=200,
    )


async def obtener_producto(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    producto_id: uuid.UUID,
) -> Producto:
    """REQ-PROD-003: 404 si no existe en la empresa actual (incluso si existe en otra)."""
    return await get_or_404(session, Producto, id_=producto_id, empresa_id=empresa_id)


async def _validar_envase(
    session: AsyncSession, *, empresa_id: uuid.UUID, envase_id: uuid.UUID | None
) -> None:
    """REQ-PROD-012: envase debe pertenecer a la empresa."""
    if envase_id is None:
        return
    if not await exists_in_empresa(session, Envase, id_=envase_id, empresa_id=empresa_id):
        raise ApiError(
            ErrorCode.VALIDACION_SEMANTICA,
            "El envase no existe o pertenece a otra empresa.",
        )


async def crear_producto(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    nombre: str,
    descripcion: str | None,
    precio_unitario_default: Any | None,
    es_retornable: bool,
    envase_id: uuid.UUID | None,
    orden_display: int,
) -> Producto:
    """REQ-PROD-004: crea el producto + evento de dominio."""
    await _validar_envase(session, empresa_id=empresa_id, envase_id=envase_id)

    producto = Producto(
        empresa_id=empresa_id,
        nombre=nombre,
        descripcion=descripcion,
        precio_unitario_default=precio_unitario_default,
        es_retornable=es_retornable,
        envase_id=envase_id,
        activo=True,
        orden_display=orden_display,
    )
    session.add(producto)
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="producto",
        accion="creado",
    ) as ev:
        ev.entidad_id = producto.id
        ev.detalles["nombre"] = nombre
        ev.detalles["es_retornable"] = es_retornable

    return producto


async def actualizar_producto(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    producto_id: uuid.UUID,
    cambios: dict[str, Any],
) -> Producto:
    """REQ-PROD-007/008: PATCH parcial. Solo actualiza campos enviados.

    `cambios` es un dict con SOLO los campos que cambian (los `None` también
    se aceptan como valor nuevo — `model_dump(exclude_unset=True)` en el caller).
    """
    producto = await obtener_producto(session, empresa_id=empresa_id, producto_id=producto_id)

    if "envase_id" in cambios:
        await _validar_envase(session, empresa_id=empresa_id, envase_id=cambios["envase_id"])

    # Diff para el evento.
    diff: dict[str, dict[str, Any]] = {}
    for campo, nuevo in cambios.items():
        anterior = getattr(producto, campo)
        if anterior != nuevo:
            diff[campo] = {"de": _serializable(anterior), "a": _serializable(nuevo)}
            setattr(producto, campo, nuevo)

    if not diff:
        return producto  # nada cambió, no generamos evento

    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="producto",
        accion="modificado",
    ) as ev:
        ev.entidad_id = producto.id
        ev.detalles["diff"] = diff

    return producto


async def desactivar_producto(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    producto_id: uuid.UUID,
) -> None:
    """REQ-PROD-009/010: soft delete idempotente."""
    producto = await obtener_producto(session, empresa_id=empresa_id, producto_id=producto_id)
    if not producto.activo:
        return  # ya estaba inactivo: no-op, no genera evento duplicado

    producto.activo = False
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="producto",
        accion="desactivado",
    ) as ev:
        ev.entidad_id = producto.id


def _serializable(v: Any) -> Any:
    """Convierte valores a algo JSON-friendly para guardar en `detalles_jsonb`."""
    if isinstance(v, uuid.UUID):
        return str(v)
    from decimal import Decimal

    if isinstance(v, Decimal):
        return str(v)
    return v
