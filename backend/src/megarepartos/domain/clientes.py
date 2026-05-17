"""Domain de clientes: CRUD + búsqueda difusa + validaciones."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.domain._repository import exists_in_empresa, get_or_404
from megarepartos.infra import geocoding
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.models.cliente import Cliente, ProductoHabitual
from megarepartos.models.producto import Producto
from megarepartos.models.zona import Zona

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(slots=True)
class HabitualOut:
    producto_id: uuid.UUID
    cantidad: int
    nombre: str
    es_retornable: bool


@dataclass(slots=True)
class HabitualIn:
    producto_id: uuid.UUID
    cantidad: int


def normalizar_telefono(raw: str) -> str:
    """REQ-CLI-010: strip + agrega +54 si no empieza con +.

    Levanta `VALIDACION_INPUT` si no hay ningún dígito.
    """
    cleaned = re.sub(r"[\s\-\(\)]", "", raw.strip())
    if not re.search(r"\d", cleaned):
        raise ApiError(ErrorCode.VALIDACION_INPUT, "Teléfono debe tener al menos un dígito.")
    if not cleaned.startswith("+"):
        # Sacar el 0 inicial si está (típico AR: "0351...").
        cleaned = cleaned.lstrip("0")
        cleaned = "+54" + cleaned
    return cleaned


async def listar_clientes(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    q: str | None = None,
    modalidad: str | None = None,
    zona_id: uuid.UUID | None = None,
    activo: bool | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[Cliente], int]:
    """REQ-CLI-001..005. Devuelve `(items, total)` para paginar."""
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    stmt = select(Cliente).where(Cliente.empresa_id == empresa_id)
    count_stmt = select(func.count(Cliente.id)).where(Cliente.empresa_id == empresa_id)

    if q:
        q_normalizado = re.sub(r"[\s\-\(\)]", "", q.strip())
        like_pattern = f"%{q.strip()}%"
        # Para teléfono usamos prefix match sobre el query normalizado (si parece teléfono).
        clauses = [Cliente.nombre_completo.ilike(like_pattern)]
        if q_normalizado and re.search(r"\d", q_normalizado):
            clauses.append(Cliente.telefono.like(f"%{q_normalizado}%"))
        filter_q = or_(*clauses)
        stmt = stmt.where(filter_q)
        count_stmt = count_stmt.where(filter_q)

    if modalidad is not None:
        stmt = stmt.where(Cliente.modalidad == modalidad)
        count_stmt = count_stmt.where(Cliente.modalidad == modalidad)

    if zona_id is not None:
        stmt = stmt.where(Cliente.zona_id == zona_id)
        count_stmt = count_stmt.where(Cliente.zona_id == zona_id)

    if activo is not None:
        stmt = stmt.where(Cliente.activo.is_(activo))
        count_stmt = count_stmt.where(Cliente.activo.is_(activo))

    stmt = (
        stmt.order_by(Cliente.nombre_completo.asc(), Cliente.id.asc()).limit(limit).offset(offset)
    )

    items = list((await session.execute(stmt)).scalars().all())
    total = (await session.execute(count_stmt)).scalar_one()
    return items, int(total)


async def obtener_cliente(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> Cliente:
    """REQ-CLI-006."""
    return await get_or_404(session, Cliente, id_=cliente_id, empresa_id=empresa_id)


async def _validar_zona(
    session: AsyncSession, *, empresa_id: uuid.UUID, zona_id: uuid.UUID | None
) -> None:
    """REQ-CLI-009."""
    if zona_id is None:
        return
    if not await exists_in_empresa(session, Zona, id_=zona_id, empresa_id=empresa_id):
        raise ApiError(
            ErrorCode.VALIDACION_SEMANTICA,
            "La zona no existe o pertenece a otra empresa.",
        )


async def crear_cliente(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    nombre_completo: str,
    telefono: str,
    email: str | None,
    direccion: str | None,
    zona_id: uuid.UUID | None,
    modalidad: str,
    frecuencia: str | None,
    observaciones_permanentes: str | None,
    condicion_pago: str,
) -> Cliente:
    """REQ-CLI-007/008/009/010/013."""
    await _validar_zona(session, empresa_id=empresa_id, zona_id=zona_id)
    telefono_norm = normalizar_telefono(telefono)

    # REQ-GEO-004: best-effort geocoding si hay dirección.
    coords = await geocoding.geocodear(direccion) if direccion else None

    cliente = Cliente(
        empresa_id=empresa_id,
        nombre_completo=nombre_completo.strip(),
        telefono=telefono_norm,
        email=email,
        direccion=direccion,
        coordenadas_lat=coords[0] if coords else None,
        coordenadas_lng=coords[1] if coords else None,
        zona_id=zona_id,
        modalidad=modalidad,
        frecuencia=frecuencia,
        observaciones_permanentes=observaciones_permanentes,
        condicion_pago=condicion_pago,
        activo=True,
    )
    session.add(cliente)
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="cliente",
        accion="creado",
    ) as ev:
        ev.entidad_id = cliente.id
        ev.detalles["nombre"] = cliente.nombre_completo
        ev.detalles["telefono"] = cliente.telefono

    return cliente


async def actualizar_cliente(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    cliente_id: uuid.UUID,
    cambios: dict[str, Any],
) -> Cliente:
    """REQ-CLI-011."""
    cliente = await obtener_cliente(session, empresa_id=empresa_id, cliente_id=cliente_id)

    if "zona_id" in cambios:
        await _validar_zona(session, empresa_id=empresa_id, zona_id=cambios["zona_id"])
    if "telefono" in cambios and cambios["telefono"] is not None:
        cambios["telefono"] = normalizar_telefono(cambios["telefono"])
    if "nombre_completo" in cambios and cambios["nombre_completo"] is not None:
        cambios["nombre_completo"] = cambios["nombre_completo"].strip()
    # REQ-GEO-004: re-geocodear si cambia dirección.
    if cambios.get("direccion"):
        coords = await geocoding.geocodear(cambios["direccion"])
        if coords is not None:
            cambios["coordenadas_lat"] = coords[0]
            cambios["coordenadas_lng"] = coords[1]

    diff: dict[str, dict[str, Any]] = {}
    for campo, nuevo in cambios.items():
        anterior = getattr(cliente, campo)
        if anterior != nuevo:
            diff[campo] = {"de": _serializable(anterior), "a": _serializable(nuevo)}
            setattr(cliente, campo, nuevo)

    if not diff:
        return cliente

    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="cliente",
        accion="modificado",
    ) as ev:
        ev.entidad_id = cliente.id
        ev.detalles["diff"] = diff

    return cliente


async def desactivar_cliente(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> None:
    """REQ-CLI-012."""
    cliente = await obtener_cliente(session, empresa_id=empresa_id, cliente_id=cliente_id)
    if not cliente.activo:
        return

    cliente.activo = False
    await session.flush()

    async with event_recorder(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        entidad_tipo="cliente",
        accion="desactivado",
    ) as ev:
        ev.entidad_id = cliente.id


def _serializable(v: Any) -> Any:
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


# ---- Productos habituales ----


async def listar_productos_habituales(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> list[HabitualOut]:
    """Devuelve los productos habituales del cliente, orden alfabético."""
    await obtener_cliente(session, empresa_id=empresa_id, cliente_id=cliente_id)
    rows = (
        await session.execute(
            select(
                ProductoHabitual.producto_id,
                ProductoHabitual.cantidad,
                Producto.nombre,
                Producto.es_retornable,
            )
            .join(Producto, Producto.id == ProductoHabitual.producto_id)
            .where(ProductoHabitual.cliente_id == cliente_id)
            .order_by(Producto.nombre.asc())
        )
    ).all()
    return [
        HabitualOut(producto_id=r[0], cantidad=r[1], nombre=r[2], es_retornable=r[3]) for r in rows
    ]


async def set_productos_habituales(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    cliente_id: uuid.UUID,
    items: list[HabitualIn],
) -> list[HabitualOut]:
    """Reemplaza la lista de habituales (delete + insert).

    Valida que los productos pertenezcan a la empresa.
    """
    await obtener_cliente(session, empresa_id=empresa_id, cliente_id=cliente_id)

    if items:
        producto_ids = [it.producto_id for it in items]
        rows = (
            (
                await session.execute(
                    select(Producto.id).where(
                        Producto.id.in_(producto_ids),
                        Producto.empresa_id == empresa_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        encontrados = set(rows)
        for pid in producto_ids:
            if pid not in encontrados:
                raise ApiError(
                    ErrorCode.VALIDACION_SEMANTICA,
                    "Algún producto no existe o no pertenece a la empresa.",
                )

    await session.execute(delete(ProductoHabitual).where(ProductoHabitual.cliente_id == cliente_id))
    for it in items:
        session.add(
            ProductoHabitual(
                cliente_id=cliente_id,
                producto_id=it.producto_id,
                cantidad=it.cantidad,
            )
        )
    await session.flush()

    return await listar_productos_habituales(session, empresa_id=empresa_id, cliente_id=cliente_id)


@dataclass(slots=True)
class ClienteParaLink:
    id: uuid.UUID
    nombre_completo: str
    telefono: str


async def listar_clientes_para_links(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    zona_id: uuid.UUID | None = None,
) -> list[ClienteParaLink]:
    """Lista clientes activos (para bulk-generar links). Solo campos necesarios."""
    items, _ = await listar_clientes(
        session,
        empresa_id=empresa_id,
        zona_id=zona_id,
        activo=True,
        limit=MAX_LIMIT,
        offset=0,
    )
    return [
        ClienteParaLink(id=c.id, nombre_completo=c.nombre_completo, telefono=c.telefono)
        for c in items
    ]
