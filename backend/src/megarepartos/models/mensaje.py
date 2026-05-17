"""Modelo `mensaje_enviado` — instancia individual de envío vía WhatsApp Web.

Una campaña genera N mensajes_enviados (uno por destinatario). Snapshot de
nombre/teléfono al momento del envío (sección 5: si el cliente se borra después,
no perdemos la traza).

Regla CLAUDE.md Backend #3: INSERT en esta tabla solo desde `domain/campanas.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, uuid_pk


class MensajeEnviado(Base):
    __tablename__ = "mensaje_enviado"

    id: Mapped[uuid.UUID] = uuid_pk()
    campana_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campana.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable cuando el destinatario viene de un sheet y no matchea con clientes.
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cliente.id", ondelete="SET NULL"), nullable=True
    )
    # Snapshot al momento del envío (no se reescribe si el cliente cambia después).
    destinatario_telefono: Mapped[str] = mapped_column(String(32), nullable=False)
    destinatario_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    contenido_final: Mapped[str] = mapped_column(Text, nullable=False)
    link_unico: Mapped[str | None] = mapped_column(String(512), nullable=True)
    token_link: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    # pendiente | enviado | fallido | leido
    estado: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pendiente")
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_lectura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(String(1024), nullable=True)
