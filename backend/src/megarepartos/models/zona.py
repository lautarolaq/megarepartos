"""Modelo `zona` — agrupación geográfica de clientes con día de visita."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, uuid_pk


class Zona(Base):
    __tablename__ = "zona"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    # lunes | martes | miercoles | jueves | viernes | sabado | domingo
    dia_visita: Mapped[str | None] = mapped_column(String(16), nullable=True)
    camioneta_asignada: Mapped[str | None] = mapped_column(String(128), nullable=True)
    color_display: Mapped[str | None] = mapped_column(String(16), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
