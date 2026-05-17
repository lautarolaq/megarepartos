"""Modelos `cliente` y `producto_habitual`.

`cliente` es el destinatario final de las campañas (sodero → cliente del sodero).
`producto_habitual` es la N:N entre cliente y producto con la cantidad habitual.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from megarepartos.models.base import Base, fecha_creacion_col, uuid_pk


class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[uuid.UUID] = uuid_pk()
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    # Teléfono normalizado a formato internacional (ej "+5493515551234").
    telefono: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(512), nullable=True)
    coordenadas_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    coordenadas_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    zona_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("zona.id", ondelete="SET NULL"), nullable=True
    )
    # fijo | consulta | demanda
    modalidad: Mapped[str] = mapped_column(String(16), nullable=False, server_default="consulta")
    # semanal | quincenal | mensual
    frecuencia: Mapped[str | None] = mapped_column(String(16), nullable=True)
    observaciones_permanentes: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Lista de precios — feature futura. FK lógico, sin constraint en DB hasta que
    # se cree la tabla `lista_precios` en TASK posterior.
    lista_precios_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    # contado | cuenta_corriente
    condicion_pago: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="contado"
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    fecha_creacion: Mapped[datetime] = fecha_creacion_col()
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    ultima_consulta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultima_visita: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductoHabitual(Base):
    __tablename__ = "producto_habitual"

    id: Mapped[uuid.UUID] = uuid_pk()
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("producto.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
