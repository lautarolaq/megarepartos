"""Setup de structlog con JSON output.

Cada log lleva contexto técnico (request_id, empresa_id, usuario_id) inyectado por
middleware en TASKs posteriores. En esta etapa solo configuramos el processor chain.
"""

from __future__ import annotations

import logging
import sys

import structlog

from megarepartos.config import get_settings


def configure_logging() -> None:
    """Configura structlog + stdlib logging.

    En `app_env=local`: output legible para humanos.
    Otros entornos: JSON estructurado, recogido por Cloud Logging.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.app_env == "local":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Helper para obtener un logger configurado."""
    return structlog.get_logger(name)
