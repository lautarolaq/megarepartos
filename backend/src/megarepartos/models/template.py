"""Modelos `template_mensaje` y `template_formulario`.

Templates pueden ser presets del sistema (empresa_id NULL, es_preset=true) o
custom de una empresa (empresa_id NOT NULL).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, uuid_pk


class TemplateMensaje(Base):
    __tablename__ = "template_mensaje"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    # consulta | aviso | cobranza | encuesta
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    # Contenido con variables tipo {nombre}, {monto}, {link}, {empresa}, etc.
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    es_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class TemplateFormulario(Base):
    __tablename__ = "template_formulario"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    # confirmar_pedido | encuesta_feedback | etc.
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    config_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    es_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
