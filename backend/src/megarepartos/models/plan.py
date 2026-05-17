"""Modelo `plan`.

Los planes son configuración del sistema (Inicio, Estándar, Pro, Premium — sección 12 del SPEC).
Se referencia desde `empresa.plan_id`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class Plan(Base):
    __tablename__ = "plan"

    id: Mapped[uuid.UUID] = uuid_pk()
    nombre: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    precio_mensual: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Límites por plan: clientes, usuarios, etc. JSON flexible para evolucionar.
    limites_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    fecha_creacion: Mapped[datetime] = fecha_creacion_col()
