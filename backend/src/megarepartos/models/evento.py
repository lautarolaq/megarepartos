"""Modelo `evento_dominio` — auditoría completa de operaciones.

Cada operación de escritura genera un registro acá vía `event_recorder` de
`domain/_events.py` (regla CLAUDE.md Backend #2). Consultable por dueño de la
empresa vía `/api/eventos` (TASK posterior).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class EventoDominio(Base):
    __tablename__ = "evento_dominio"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable si es evento generado por el sistema (cron, backup, etc.).
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True
    )
    entidad_tipo: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entidad_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    # creado | modificado | borrado | exportado | enviado | etc.
    accion: Mapped[str] = mapped_column(String(32), nullable=False)
    # Diff de cambios o detalle estructurado.
    detalles_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    fecha: Mapped[datetime] = fecha_creacion_col()
    ip_origen: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
