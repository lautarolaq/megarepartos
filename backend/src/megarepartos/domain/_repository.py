"""Helpers de repositorio reutilizables.

Toda interacción con DB desde `domain/*.py` pasa por estos helpers (regla
CLAUDE.md Backend #1: filtrar por `empresa_id` siempre). Defensa en
profundidad sobre la RLS de Postgres.

Si en el futuro aparece duplicación obvia (paginación, búsqueda difusa,
soft-delete patterns), se promueven a una clase. Por ahora funciones.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.infra.errors import ApiError, ErrorCode

if TYPE_CHECKING:
    from sqlalchemy.sql import ColumnElement


async def get_or_404[T](
    session: AsyncSession,
    model: type[T],
    *,
    id_: uuid.UUID,
    empresa_id: uuid.UUID,
) -> T:
    """Devuelve la fila si pertenece a la empresa, sino levanta 404.

    NO leakea diferencia entre "no existe" y "existe pero pertenece a otra
    empresa": ambos devuelven el mismo `RECURSO_NO_ENCONTRADO`. (Regla
    CLAUDE.md Backend #10 + 10.1.6: "Devuelve 404 — no 403 — para no leak info".)
    """
    obj = (
        await session.execute(
            select(model).where(
                model.id == id_,  # type: ignore[attr-defined]
                model.empresa_id == empresa_id,  # type: ignore[attr-defined]
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise ApiError(
            ErrorCode.RECURSO_NO_ENCONTRADO,
            f"{model.__name__} no encontrado.",
        )
    return obj


async def list_by_empresa[T](
    session: AsyncSession,
    model: type[T],
    *,
    empresa_id: uuid.UUID,
    filters: Sequence[ColumnElement[bool]] | None = None,
    order_by: Sequence[Any] | None = None,
    limit: int | None = None,
) -> list[T]:
    """Devuelve filas de la empresa, opcionalmente filtradas/ordenadas/limitadas.

    `filters` son expresiones SQLAlchemy adicionales (ej `[Producto.activo == True]`).
    `order_by` es una lista de columnas/expresiones SQLAlchemy.
    """
    stmt = select(model).where(model.empresa_id == empresa_id)  # type: ignore[attr-defined]
    if filters:
        for f in filters:
            stmt = stmt.where(f)
    if order_by:
        stmt = stmt.order_by(*order_by)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def exists_in_empresa[T](
    session: AsyncSession,
    model: type[T],
    *,
    id_: uuid.UUID,
    empresa_id: uuid.UUID,
) -> bool:
    """Helper liviano para validar FK opcionales (`envase_id`, etc.)."""
    stmt = select(model.id).where(  # type: ignore[attr-defined]
        model.id == id_,  # type: ignore[attr-defined]
        model.empresa_id == empresa_id,  # type: ignore[attr-defined]
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None
