"""Modelos `respuesta_link` y `confirmacion_pedido`.

Cuando un cliente abre el link público del WhatsApp, se registra una `respuesta_link`.
Si el formulario es de tipo "confirmar pedido", se crea adicionalmente una
`confirmacion_pedido` con los productos y envases concretos.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class RespuestaLink(Base):
    __tablename__ = "respuesta_link"

    id: Mapped[uuid.UUID] = uuid_pk()
    mensaje_enviado_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mensaje_enviado.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_usado: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_acceso: Mapped[datetime] = fecha_creacion_col()
    ip_acceso: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # confirmo | rechazo | en_proceso
    accion: Mapped[str] = mapped_column(String(16), nullable=False, server_default="en_proceso")
    # Respuestas del formulario (estructura libre según template).
    datos_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    fecha_accion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConfirmacionPedido(Base):
    __tablename__ = "confirmacion_pedido"

    id: Mapped[uuid.UUID] = uuid_pk()
    respuesta_link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("respuesta_link.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cliente.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    fecha_propuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    productos_solicitados: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    envases_a_devolver: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    observacion_cliente: Mapped[str | None] = mapped_column(String(2048), nullable=True)
