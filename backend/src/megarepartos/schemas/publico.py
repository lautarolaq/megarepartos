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
    zona_nombre: str | None = None
    zona_dia_visita: str | None = None
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
    # Opcional: si la respuesta viene desde una campaña (broadcast o bulk
    # individual), el frontend manda el campana_id para taggear el evento.
    campana_id: str | None = None
    # Opcional: si el cliente confirmó pese a una zona mismatch detectada en
    # la landing, se propaga el flag al evento para que el sodero lo vea.
    zona_mismatch: bool = False


class GenerarLinkOut(BaseModel):
    """Respuesta de `POST /api/clientes/{id}/generar-link` (admin)."""

    url: str
    token: str
    expira_en_dias: int


class LinkBulkItem(BaseModel):
    """Un cliente + su link público en la respuesta bulk."""

    cliente_id: str
    nombre_completo: str
    telefono: str
    url: str


class GenerarLinksBulkIn(BaseModel):
    """Body de `POST /api/clientes/generar-links-bulk` (admin).

    Opcional: filtra por zona. Si no se pasa nada, devuelve para TODOS los
    clientes activos de la empresa (cuidado con el peso si la base es grande).
    """

    zona_id: str | None = None
    # Opcionales: label + mensaje snapshot para la campaña asociada.
    nombre: str | None = None
    mensaje: str | None = None


class GenerarLinksBulkOut(BaseModel):
    items: list[LinkBulkItem]
    campana_id: str | None = None


# Broadcast -----------------------------------------------------------------


class GenerarLinkBroadcastIn(BaseModel):
    """Body de `POST /api/clientes/generar-link-broadcast` (admin)."""

    nombre: str  # Label de la campaña para el sodero ("Miércoles zona norte 22/05")
    mensaje: str  # Snapshot del mensaje (con {link} si quiere embed)
    zona_id: str | None = None  # Filtro opcional para anotar la campaña


class GenerarLinkBroadcastOut(BaseModel):
    """Respuesta de `POST /api/clientes/generar-link-broadcast` (admin)."""

    url: str
    token: str
    expira_en_dias: int
    campana_id: str


class IdentificarBroadcastIn(BaseModel):
    """Body de `POST /api/publico/b/{token}/identificar`."""

    telefono: str


class IdentificarBroadcastOut(BaseModel):
    """Respuesta — devuelve datos del cliente, un token personal de corta
    duración y el `campana_id` para que el frontend pueda taggear la respuesta
    cuando la postee a `/api/publico/c/{token}/respuesta`.

    `zona_mismatch` es true si la campaña era para una zona X pero el cliente
    pertenece a la zona Y (≠ X). El frontend muestra un aviso al cliente para
    confirmar que es intencional. Útil para detectar broadcasts cruzados (el
    sodero mandó link de Norte a alguien de Centro, o alguien forwardeo el
    link a un amigo de otra zona).
    """

    cliente_token: str
    campana_id: str
    info: LinkPublicoOut
    zona_mismatch: bool = False
    campana_zona_nombre: str | None = None
    cliente_zona_nombre: str | None = None
