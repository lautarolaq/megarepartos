"""Modelo `empresa` — tenant raíz del sistema multi-tenant."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class Empresa(Base):
    __tablename__ = "empresa"

    id: Mapped[uuid.UUID] = uuid_pk()
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    # sodería | garrafas | verduras | viandas | distribuidora | otro
    tipo_negocio: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plan.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # trial | activa | suspendida | cancelada
    estado_suscripcion: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="trial"
    )
    fecha_creacion: Mapped[datetime] = fecha_creacion_col()
    fecha_cancelacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    direccion_deposito: Mapped[str | None] = mapped_column(String(512), nullable=True)
    coordenadas_deposito_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    coordenadas_deposito_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="America/Argentina/Cordoba"
    )
    config_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
