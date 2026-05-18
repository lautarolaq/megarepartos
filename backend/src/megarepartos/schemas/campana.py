"""Schemas Pydantic para `/api/campanas/*`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CampanaResumenOut(BaseModel):
    id: str
    nombre: str
    tipo_envio: str  # broadcast | bulk_individual
    zona_id: str | None
    zona_nombre: str | None
    mensaje: str
    fecha_creacion: datetime
    n_confirmados: int
    n_rechazados: int


class CampanaListOut(BaseModel):
    items: list[CampanaResumenOut]


class RespuestaCampanaOut(BaseModel):
    cliente_id: str
    cliente_nombre: str
    cliente_telefono: str
    accion: str  # confirmo | rechazo
    fecha: datetime
    productos: list[dict[str, Any]]


class CampanaDetalleOut(BaseModel):
    id: str
    nombre: str
    tipo_envio: str
    zona_id: str | None
    zona_nombre: str | None
    mensaje: str
    fecha_creacion: datetime
    respuestas: list[RespuestaCampanaOut]
