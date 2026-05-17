"""Modelo `sheet_referencia` — registro de Google Sheets creados/usados por la app."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class SheetReferencia(Base):
    __tablename__ = "sheet_referencia"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # importacion_clientes | cobranzas | export_confirmados | export_ruta | encuesta
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    google_sheet_id: Mapped[str] = mapped_column(String(128), nullable=False)
    google_sheet_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_creacion: Mapped[datetime] = fecha_creacion_col()
    fecha_ultima_lectura: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # activo | procesado | archivado
    estado: Mapped[str] = mapped_column(String(16), nullable=False, server_default="activo")
    campana_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campana.id", ondelete="SET NULL"), nullable=True
    )
