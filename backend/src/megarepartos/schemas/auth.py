"""Schemas Pydantic para autenticación: I/O de los endpoints `/api/auth/*`."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class GoogleAuthUrl(BaseModel):
    """Respuesta de `GET /api/auth/google/url`."""

    url: str


class AccessTokenOut(BaseModel):
    """Respuesta cuando emitimos un access token (refresh, etc.)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UsuarioOut(BaseModel):
    """Vista pública de un Usuario (sin tokens ni datos sensibles)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nombre: str
    rol: str
    activo: bool


class EmpresaOut(BaseModel):
    """Vista pública de una Empresa."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    tipo_negocio: str
    estado_suscripcion: str
    timezone: str


class MeOut(BaseModel):
    """Respuesta de `GET /api/auth/me`."""

    usuario: UsuarioOut
    empresa: EmpresaOut
