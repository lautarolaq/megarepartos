"""Schemas Pydantic para `/api/empresa/*`."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoNegocio = Literal["soderia", "garrafas", "verduras", "viandas", "distribuidora", "otro"]


class EmpresaOut(BaseModel):
    """No usa from_attributes porque `mensaje_default_link` se lee de
    `config_jsonb`, no es una columna directa.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    tipo_negocio: str
    estado_suscripcion: str
    direccion_deposito: str | None
    timezone: str
    mensaje_default_link: str | None = None


class EmpresaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    tipo_negocio: TipoNegocio | None = None
    direccion_deposito: str | None = Field(default=None, max_length=512)
    timezone: str | None = Field(default=None, max_length=64)
    # Plantilla para el mensaje de WhatsApp al mandar el link. Soporta
    # variables {nombre} y {link}. Persiste en empresa.config_jsonb.
    mensaje_default_link: str | None = Field(default=None, max_length=2048)
