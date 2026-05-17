"""Schemas Pydantic para `/api/clientes`."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Modalidad = Literal["fijo", "consulta", "demanda"]
Frecuencia = Literal["semanal", "quincenal", "mensual"]
CondicionPago = Literal["contado", "cuenta_corriente"]


class ClienteCreate(BaseModel):
    nombre_completo: str = Field(min_length=1, max_length=255)
    telefono: str = Field(min_length=1, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    direccion: str | None = Field(default=None, max_length=512)
    zona_id: uuid.UUID | None = None
    modalidad: Modalidad = "consulta"
    frecuencia: Frecuencia | None = None
    observaciones_permanentes: str | None = Field(default=None, max_length=2048)
    condicion_pago: CondicionPago = "contado"


class ClienteUpdate(BaseModel):
    nombre_completo: str | None = Field(default=None, min_length=1, max_length=255)
    telefono: str | None = Field(default=None, min_length=1, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    direccion: str | None = Field(default=None, max_length=512)
    zona_id: uuid.UUID | None = None
    modalidad: Modalidad | None = None
    frecuencia: Frecuencia | None = None
    observaciones_permanentes: str | None = Field(default=None, max_length=2048)
    condicion_pago: CondicionPago | None = None
    activo: bool | None = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre_completo: str
    telefono: str
    email: str | None
    direccion: str | None
    zona_id: uuid.UUID | None
    modalidad: str
    frecuencia: str | None
    observaciones_permanentes: str | None
    condicion_pago: str
    activo: bool


class ClienteListOut(BaseModel):
    items: list[ClienteOut]
    total: int
    limit: int
    offset: int
