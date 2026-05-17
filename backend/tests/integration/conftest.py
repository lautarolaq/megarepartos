"""Fixtures para tests de integración: Postgres testcontainer (session) +
engine + session por-test con rollback + httpx client.

Patrón clave: el **container** Postgres es session-scoped (caro, ~3-5s al
arrancar), pero el **engine async** se crea por test. Eso evita el clásico
problema "Future attached to a different loop" sin pagar el costo de levantar
Postgres en cada test.

El schema se aplica una sola vez al inicio de la sesión vía `alembic upgrade head`.
Cada test corre dentro de una transacción "outer" sobre una connection nueva;
al final, la transacción se rollbackea.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from megarepartos.config import get_settings
from megarepartos.infra.db import get_session
from megarepartos.main import app


def _to_async_url(sync_url: str) -> str:
    """`postgresql://...` → `postgresql+asyncpg://...`."""
    if "+asyncpg" in sync_url:
        return sync_url
    return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://", 1
    )


@pytest.fixture(scope="session")
def monkeypatch_session() -> Iterator[pytest.MonkeyPatch]:
    """`MonkeyPatch` con scope session (pytest no lo ofrece built-in)."""
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="session")
def postgres_url(monkeypatch_session: pytest.MonkeyPatch) -> Iterator[str]:
    """Levanta un container Postgres efímero y corre alembic upgrade head."""
    with PostgresContainer("postgres:16-alpine") as pg:
        async_url = _to_async_url(pg.get_connection_url())
        monkeypatch_session.setenv("DATABASE_URL", async_url)
        get_settings.cache_clear()

        backend_dir = Path(__file__).resolve().parents[2]
        alembic_cfg = Config(str(backend_dir / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
        command.upgrade(alembic_cfg, "head")

        yield async_url


@pytest_asyncio.fixture
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    """Engine por test: NullPool para que la connection no sobreviva al test
    (evita "Future attached to a different loop")."""
    eng = create_async_engine(postgres_url, poolclass=NullPool)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Sesión transaccional. Al final del test se rollbackea.

    Uso `join_transaction_mode="create_savepoint"` para que los `session.commit()`
    del endpoint cierren un savepoint en vez de la transacción outer — así
    todo es reversible.
    """
    connection: AsyncConnection = await engine.connect()
    outer_tx = await connection.begin()
    sessionmaker = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=AsyncSession,
        join_transaction_mode="create_savepoint",
    )
    session = sessionmaker()
    try:
        yield session
    finally:
        await session.close()
        if outer_tx.is_active:
            await outer_tx.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def app_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """`httpx.AsyncClient` con `get_session` apuntando al `db_session` del test."""

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
