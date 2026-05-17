"""Schemas Pydantic para `/api/publico/c/{token}` (sin auth)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class EmpresaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre: str


class ClientePublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre_completo: str
    telefono: str


class LinkPublicoOut(BaseModel):
    """Lo que el cliente ve al abrir el link."""

    empresa: EmpresaPublica
    cliente: ClientePublico


class RespuestaIn(BaseModel):
    """Payload del POST de respuesta del cliente."""

    accion: Literal["confirmo", "rechazo"]
    datos: dict[str, Any] = {}


class GenerarLinkOut(BaseModel):
    """Respuesta de `POST /api/clientes/{id}/generar-link` (admin)."""

    url: str
    token: str
    expira_en_dias: int
