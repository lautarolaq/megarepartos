"""Modelo `token_extension` — credencial de la extensión Chrome instalada por el usuario.

Cada instalación de la extensión genera un token único que se valida en cada envío
contra el backend (regla CLAUDE.md Extensión #3).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class TokenExtension(Base):
    __tablename__ = "token_extension"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    fecha_creacion: Mapped[datetime] = fecha_creacion_col()
    fecha_ultima_validacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revocado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    detalles_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
