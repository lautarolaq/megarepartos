"""FastAPI app entrypoint.

En TASK-000 solo expone `/health`. Los routers de negocio (auth, empresa, clientes, etc.)
se montan en TASKs posteriores.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos import __version__
from megarepartos.config import get_settings
from megarepartos.infra.db import engine, get_session
from megarepartos.infra.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configura logging al startup y cierra el engine al shutdown."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()
    logger.info(
        "app.startup",
        version=__version__,
        env=settings.app_env,
    )
    try:
        yield
    finally:
        await engine.dispose()
        logger.info("app.shutdown")


app = FastAPI(
    title="Megarepartos API",
    version=__version__,
    lifespan=lifespan,
)


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@app.get("/health", tags=["meta"])
async def health(session: SessionDep) -> dict[str, str]:
    """Healthcheck para Cloud Run / uptime monitoring.

    Devuelve `{status: ok, db: ok}` si la app responde y la DB acepta `SELECT 1`.
    Si la DB falla, marca `db: error` pero mantiene 200 para no tirar abajo todo
    el servicio por un blip momentáneo (Cloud Run igual tiene su propio check).
    """
    db_status = "ok"
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
    except Exception:
        db_status = "error"

    return {"status": "ok", "db": db_status}
