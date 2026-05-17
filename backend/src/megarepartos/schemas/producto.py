"""Schemas Pydantic para `/api/productos`."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductoCreate(BaseModel):
    """Input para `POST /api/productos`."""

    nombre: str = Field(min_length=1, max_length=128)
    descripcion: str | None = Field(default=None, max_length=1024)
    precio_unitario_default: Decimal | None = Field(default=None, ge=0)
    es_retornable: bool = False
    envase_id: uuid.UUID | None = None
    orden_display: int = 0


class ProductoUpdate(BaseModel):
    """Input para `PATCH /api/productos/{id}` — todos los campos opcionales."""

    nombre: str | None = Field(default=None, min_length=1, max_length=128)
    descripcion: str | None = Field(default=None, max_length=1024)
    precio_unitario_default: Decimal | None = Field(default=None, ge=0)
    es_retornable: bool | None = None
    envase_id: uuid.UUID | None = None
    activo: bool | None = None
    orden_display: int | None = None


class ProductoOut(BaseModel):
    """Vista pública de un Producto."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    precio_unitario_default: Decimal | None
    es_retornable: bool
    envase_id: uuid.UUID | None
    activo: bool
    orden_display: int


class ProductoListOut(BaseModel):
    """Respuesta de `GET /api/productos`."""

    items: list[ProductoOut]
