"""Schemas Pydantic para `/api/usuarios`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Rol = Literal["admin", "operador"]


class UsuarioUpdate(BaseModel):
    rol: Rol | None = None
    activo: bool | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nombre: str
    rol: str
    activo: bool
    ultima_sesion: datetime | None


class UsuarioListOut(BaseModel):
    items: list[UsuarioOut]
