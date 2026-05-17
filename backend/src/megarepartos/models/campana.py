"""Modelo `campana` — unidad operativa que combina destinatarios + mensaje + form."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class Campana(Base):
    __tablename__ = "campana"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_creador_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    # consulta | aviso | cobranza | encuesta
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    template_mensaje_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("template_mensaje.id", ondelete="RESTRICT"), nullable=False
    )
    template_formulario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("template_formulario.id", ondelete="RESTRICT"), nullable=True
    )
    # borrador | programada | enviando | enviada | cerrada
    estado: Mapped[str] = mapped_column(String(16), nullable=False, server_default="borrador")
    fecha_programada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_envio_inicio: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_envio_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Origen de destinatarios: filtros aplicados o sheet_id (jsonb).
    destinatarios_origen: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    estadisticas: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    fecha_creacion: Mapped[datetime] = fecha_creacion_col()
