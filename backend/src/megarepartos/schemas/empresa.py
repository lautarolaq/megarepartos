"""Schemas Pydantic para `/api/empresa/*`."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoNegocio = Literal["soderia", "garrafas", "verduras", "viandas", "distribuidora", "otro"]


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    tipo_negocio: str
    estado_suscripcion: str
    direccion_deposito: str | None
    timezone: str


class EmpresaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    tipo_negocio: TipoNegocio | None = None
    direccion_deposito: str | None = Field(default=None, max_length=512)
    timezone: str | None = Field(default=None, max_length=64)
