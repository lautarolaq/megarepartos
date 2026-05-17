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


class ProductoHabitualPublico(BaseModel):
    """Un producto que el cliente compra habitualmente."""

    producto_id: str
    nombre: str
    cantidad_habitual: int
    es_retornable: bool


class LinkPublicoOut(BaseModel):
    """Lo que el cliente ve al abrir el link."""

    empresa: EmpresaPublica
    cliente: ClientePublico
    productos_habituales: list[ProductoHabitualPublico]


class ProductoSolicitado(BaseModel):
    """Item en la respuesta de confirmar pedido."""

    producto_id: str
    cantidad_llenos: int = 0
    cantidad_vacios: int = 0  # solo aplica si el producto es retornable


class RespuestaIn(BaseModel):
    """Payload del POST de respuesta del cliente."""

    accion: Literal["confirmo", "rechazo"]
    productos: list[ProductoSolicitado] = []
    observacion: str | None = None
    datos: dict[str, Any] = {}


class GenerarLinkOut(BaseModel):
    """Respuesta de `POST /api/clientes/{id}/generar-link` (admin)."""

    url: str
    token: str
    expira_en_dias: int
