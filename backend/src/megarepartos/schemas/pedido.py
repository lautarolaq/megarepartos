"""Schemas Pydantic para `/api/pedidos` — respuestas de clientes vía link público.

Los pedidos no son una tabla propia: se persisten como `evento_dominio` con
`accion="respondio_link"` (ver `api/publico.py` POST /respuesta). Este schema
es la proyección que ve el admin en el dashboard.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ProductoPedido(BaseModel):
    """Item de un pedido tal como se guardó en `evento_dominio.detalles_jsonb`."""

    producto_id: str
    nombre: str
    cantidad_llenos: int
    cantidad_vacios: int
    es_retornable: bool


class PedidoOut(BaseModel):
    """Respuesta de un cliente a un link público."""

    evento_id: uuid.UUID
    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_telefono: str
    cliente_direccion: str | None = None
    cliente_zona_id: uuid.UUID | None = None
    cliente_zona_nombre: str | None = None
    accion: str  # "confirmo" | "rechazo"
    productos: list[ProductoPedido] = []
    observacion: str | None = None
    fecha: datetime


class PedidoListOut(BaseModel):
    items: list[PedidoOut]
    total: int
    limit: int
    offset: int


class PedidoStatsOut(BaseModel):
    """Resumen rápido para el dashboard."""

    pedidos_hoy: int
    confirmados_hoy: int
    pedidos_semana: int
    clientes_activos: int


class PendienteOut(BaseModel):
    """Cliente al que se le mandó el link y todavía no respondió."""

    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_telefono: str
    fecha_link: datetime


class PendientesListOut(BaseModel):
    items: list[PendienteOut]
    total: int


class HistorialEventoOut(BaseModel):
    """Una entrada del historial de un cliente."""

    evento_id: uuid.UUID
    accion: str  # "respondio_link" | "link_generado"
    fecha: datetime
    detalles: dict


class HistorialClienteOut(BaseModel):
    items: list[HistorialEventoOut]
    total: int
