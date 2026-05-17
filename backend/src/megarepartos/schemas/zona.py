"""Schemas Pydantic para `/api/zonas`."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DiaSemana = Literal["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class ZonaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=128)
    dia_visita: DiaSemana | None = None
    camioneta_asignada: str | None = Field(default=None, max_length=128)
    color_display: str | None = Field(default=None, max_length=16)


class ZonaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=128)
    dia_visita: DiaSemana | None = None
    camioneta_asignada: str | None = Field(default=None, max_length=128)
    color_display: str | None = Field(default=None, max_length=16)
    activo: bool | None = None


class ZonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    dia_visita: str | None
    camioneta_asignada: str | None
    color_display: str | None
    activo: bool


class ZonaListOut(BaseModel):
    items: list[ZonaOut]
