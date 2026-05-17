"""FastAPI app entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos import __version__
from megarepartos.api import auth as auth_router
from megarepartos.api import clientes as clientes_router
from megarepartos.api import envases as envases_router
from megarepartos.api import pedidos as pedidos_router
from megarepartos.api import productos as productos_router
from megarepartos.api import publico as publico_router
from megarepartos.api import usuarios as usuarios_router
from megarepartos.api import zonas as zonas_router
from megarepartos.config import get_settings
from megarepartos.infra.audit_context import AuditContextMiddleware
from megarepartos.infra.db import engine, get_session
from megarepartos.infra.errors import ApiError, ErrorCode
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

# CORS: en local permitimos `localhost:5173` (Vite dev server). En prod,
# el frontend va a estar en el mismo dominio que el backend (Cloud Run +
# Cloud Storage), pero por las dudas dejamos configurable.
_settings = get_settings()
_allowed_origins = (
    ["http://localhost:5173", "http://127.0.0.1:5173"]
    if _settings.app_env == "local"
    else []  # producción: same-origin, no CORS necesario
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,  # necesario para que el browser mande la cookie mr_refresh
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Middleware antes de los routers — captura request_id, ip, user_agent para
# que `event_recorder` los lea desde contextvars.
app.add_middleware(AuditContextMiddleware)

app.include_router(auth_router.router)
app.include_router(productos_router.router)
app.include_router(envases_router.router)
app.include_router(zonas_router.router)
app.include_router(clientes_router.router)
app.include_router(usuarios_router.router)
app.include_router(publico_router.router)
app.include_router(pedidos_router.router)


@app.exception_handler(ApiError)
async def _api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    """Mapea `ApiError` al body estándar `{error: {code, message, details}}`."""
    return JSONResponse(status_code=exc.http_status, content=exc.to_body())


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic / FastAPI validation errors → 400 VALIDACION_INPUT."""
    err = ApiError(
        ErrorCode.VALIDACION_INPUT,
        "Input inválido.",
        details={"errors": exc.errors()},
    )
    return JSONResponse(status_code=err.http_status, content=err.to_body())


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
