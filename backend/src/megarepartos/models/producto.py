"""Modelos `producto` y `envase`.

Se agrupan acá según la estructura de la sección 17 del SPEC.
Productos son lo que vende la empresa; envases son los recipientes retornables
asociados a productos (ej. bidón 20L).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, uuid_pk


class Envase(Base):
    __tablename__ = "envase"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    valor_referencial: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Producto(Base):
    __tablename__ = "producto"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    precio_unitario_default: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    es_retornable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    envase_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("envase.id", ondelete="SET NULL"), nullable=True
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    orden_display: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
