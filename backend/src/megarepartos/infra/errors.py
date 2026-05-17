"""Catálogo de errores de la API (sección "Catálogo de errores estándar" de CLAUDE.md).

`ApiError` es la excepción que se levanta desde dominio. El handler de FastAPI en
`main.py` la traduce al body estándar `{error: {code, message, details}}`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    AUTH_REQUIRED = "AUTH_REQUIRED"  # 401
    AUTH_INVALID = "AUTH_INVALID"  # 401
    PERMISO_DENEGADO = "PERMISO_DENEGADO"  # 403
    RECURSO_NO_ENCONTRADO = "RECURSO_NO_ENCONTRADO"  # 404
    VALIDACION_INPUT = "VALIDACION_INPUT"  # 400
    VALIDACION_SEMANTICA = "VALIDACION_SEMANTICA"  # 422
    CONFLICTO_ESTADO = "CONFLICTO_ESTADO"  # 409
    LIMITE_PLAN = "LIMITE_PLAN"  # 402
    RATE_LIMIT = "RATE_LIMIT"  # 429
    EXTERNO_FALLO = "EXTERNO_FALLO"  # 503
    INTERNO = "INTERNO"  # 500


# Mapeo a HTTP status. Single source of truth.
HTTP_STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.AUTH_REQUIRED: 401,
    ErrorCode.AUTH_INVALID: 401,
    ErrorCode.PERMISO_DENEGADO: 403,
    ErrorCode.RECURSO_NO_ENCONTRADO: 404,
    ErrorCode.VALIDACION_INPUT: 400,
    ErrorCode.VALIDACION_SEMANTICA: 422,
    ErrorCode.CONFLICTO_ESTADO: 409,
    ErrorCode.LIMITE_PLAN: 402,
    ErrorCode.RATE_LIMIT: 429,
    ErrorCode.EXTERNO_FALLO: 503,
    ErrorCode.INTERNO: 500,
}


@dataclass(slots=True)
class ApiError(Exception):
    """Excepción canónica del backend.

    Se levanta desde `domain/` y `infra/`. El handler en `main.py` la traduce al
    body estándar `{error: {code, message, details}}` con el status HTTP correcto.
    """

    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def http_status(self) -> int:
        return HTTP_STATUS_BY_CODE[self.code]

    def to_body(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            }
        }
