"""Schemas Pydantic para `/api/envases`."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class EnvaseCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=128)
    valor_referencial: Decimal | None = Field(default=None, ge=0)


class EnvaseUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=128)
    valor_referencial: Decimal | None = Field(default=None, ge=0)
    activo: bool | None = None


class EnvaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    valor_referencial: Decimal | None
    activo: bool


class EnvaseListOut(BaseModel):
    items: list[EnvaseOut]
