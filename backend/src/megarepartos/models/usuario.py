"""Modelo `usuario` — miembro de una empresa."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        # Un mismo email no puede repetirse dentro de la misma empresa.
        UniqueConstraint("empresa_id", "email", name="uq_usuario_empresa_email"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    # admin | operador
    rol: Mapped[str] = mapped_column(String(16), nullable=False, server_default="operador")
    # Token OAuth de Google (encriptado en TASK-001). Nullable porque algunos usuarios
    # pueden invitarse antes de su primer login.
    google_oauth_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    google_oauth_scopes: Mapped[list[str] | None] = mapped_column(ARRAY(String(128)), nullable=True)
    ultima_sesion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    fecha_creacion: Mapped[datetime] = fecha_creacion_col()
