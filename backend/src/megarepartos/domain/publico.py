"""Domain del link público — cliente final que abre la URL firmada.

Los endpoints en `api/publico.py` no tienen `empresa_id` en claims (el cliente
no está autenticado), así que hacen `RESET ROLE` para bypass RLS y delegan
acá la validación + lookup del cliente.

NOTA: estas funciones asumen que la sesión está corriendo como superuser
(via `RESET ROLE` previo). Hacer `set_tenant_context` antes rompe la query
porque el cliente no se conoce sin antes resolverlo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.models.cliente import Cliente, ProductoHabitual
from megarepartos.models.empresa import Empresa
from megarepartos.models.producto import Producto
from megarepartos.models.zona import Zona


@dataclass(slots=True)
class HabitualPublico:
    producto_id: str
    nombre: str
    cantidad_habitual: int
    es_retornable: bool


@dataclass(slots=True)
class LinkPublicoData:
    empresa_nombre: str
    cliente_nombre_completo: str
    cliente_telefono: str
    zona_nombre: str | None = None
    zona_dia_visita: str | None = None
    productos_habituales: list[HabitualPublico] = field(default_factory=list)


@dataclass(slots=True)
class ProductoRespuesta:
    producto_id: str
    cantidad_llenos: int
    cantidad_vacios: int


async def obtener_info_link(
    session: AsyncSession,
    *,
    cliente_id: uuid.UUID,
) -> LinkPublicoData:
    """REQ-LINK-003/004: devuelve empresa + cliente + productos habituales.

    El caller debe haber hecho `RESET ROLE` antes (no hay tenant context).
    Levanta `RECURSO_NO_ENCONTRADO` si el cliente no existe o está inactivo.
    """
    cliente = (
        await session.execute(select(Cliente).where(Cliente.id == cliente_id))
    ).scalar_one_or_none()
    if cliente is None or not cliente.activo:
        raise ApiError(ErrorCode.RECURSO_NO_ENCONTRADO, "El link no es válido.")

    empresa = (
        await session.execute(select(Empresa).where(Empresa.id == cliente.empresa_id))
    ).scalar_one()

    zona_nombre: str | None = None
    zona_dia_visita: str | None = None
    if cliente.zona_id:
        zona = (
            await session.execute(select(Zona).where(Zona.id == cliente.zona_id))
        ).scalar_one_or_none()
        if zona is not None:
            zona_nombre = zona.nombre
            zona_dia_visita = zona.dia_visita

    rows = (
        await session.execute(
            select(
                ProductoHabitual.producto_id,
                ProductoHabitual.cantidad,
                Producto.nombre,
                Producto.es_retornable,
            )
            .join(Producto, Producto.id == ProductoHabitual.producto_id)
            .where(ProductoHabitual.cliente_id == cliente_id, Producto.activo.is_(True))
            .order_by(Producto.nombre.asc())
        )
    ).all()

    return LinkPublicoData(
        empresa_nombre=empresa.nombre,
        cliente_nombre_completo=cliente.nombre_completo,
        cliente_telefono=cliente.telefono,
        zona_nombre=zona_nombre,
        zona_dia_visita=zona_dia_visita,
        productos_habituales=[
            HabitualPublico(
                producto_id=str(r[0]),
                cantidad_habitual=r[1],
                nombre=r[2],
                es_retornable=r[3],
            )
            for r in rows
        ],
    )


async def registrar_respuesta(
    session: AsyncSession,
    *,
    cliente_id: uuid.UUID,
    accion: str,
    productos: list[ProductoRespuesta],
    observacion: str | None,
) -> uuid.UUID:
    """REQ-LINK-005/006: resuelve empresa del cliente y persiste evento_dominio.

    El caller debe haber hecho `RESET ROLE` antes. Devuelve el empresa_id.
    """
    empresa_id = (
        await session.execute(
            text("SELECT empresa_id FROM cliente WHERE id = :id AND activo = true"),
            {"id": cliente_id},
        )
    ).scalar_one_or_none()
    if empresa_id is None:
        raise ApiError(ErrorCode.RECURSO_NO_ENCONTRADO, "El link no es válido.")

    productos_detalle: list[dict[str, Any]] = []
    if productos:
        ids = [p.producto_id for p in productos]
        nombres_rows = (
            await session.execute(
                text("SELECT id::text, nombre, es_retornable FROM producto WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
        ).all()
        nombres = {r[0]: (r[1], r[2]) for r in nombres_rows}
        for p in productos:
            nombre, es_retornable = nombres.get(p.producto_id, (p.producto_id, False))
            productos_detalle.append(
                {
                    "producto_id": p.producto_id,
                    "nombre": nombre,
                    "cantidad_llenos": p.cantidad_llenos,
                    "cantidad_vacios": p.cantidad_vacios,
                    "es_retornable": es_retornable,
                }
            )

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=None,
        entidad_tipo="cliente",
        accion="respondio_link",
    ) as ev:
        ev.entidad_id = cliente_id
        ev.detalles["accion"] = accion
        ev.detalles["productos"] = productos_detalle
        ev.detalles["observacion"] = observacion

    return empresa_id
