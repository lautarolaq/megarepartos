"""SQLAlchemy async engine + sesión.

Toda interacción con DB pasa por este módulo. Async always (regla CLAUDE.md Backend #8).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from megarepartos.config import get_settings


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.effective_database_url,
        echo=settings.app_env == "local" and settings.log_level == "DEBUG",
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


engine: AsyncEngine = _build_engine()
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: yields una `AsyncSession` por request."""
    async with SessionLocal() as session:
        yield session


async def set_tenant_context(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> None:
    """Setea los session vars que las RLS policies leen.

    Usa `set_config(..., is_local=true)` que es equivalente a `SET LOCAL`:
    el valor dura hasta el final de la transacción actual. Si el caller
    no abrió una transacción explícita, asyncpg/SQLAlchemy crean una al
    primer statement — el `set_config` se ejecuta dentro de esa.

    Idempotente: llamarlo dos veces dentro de la misma transacción es OK.
    """
    await session.execute(
        text("SELECT set_config('app.empresa_id', :empresa_id, true)"),
        {"empresa_id": str(empresa_id)},
    )
    await session.execute(
        text("SELECT set_config('app.usuario_id', :usuario_id, true)"),
        {"usuario_id": str(usuario_id)},
    )
