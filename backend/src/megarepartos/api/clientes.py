"""Router `/api/clientes/*` — CRUD con búsqueda y paginación."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.domain.clientes import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    actualizar_cliente,
    crear_cliente,
    desactivar_cliente,
    listar_clientes,
    obtener_cliente,
)
from megarepartos.infra.auth import (
    LINK_TOKEN_DEFAULT_TTL_SECONDS,
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
    sign_link_token,
)
from megarepartos.schemas.cliente import (
    ClienteCreate,
    ClienteListOut,
    ClienteOut,
    ClienteUpdate,
    ProductoHabitualItemOut,
    ProductosHabitualesOut,
    SetProductosHabitualesIn,
)
from megarepartos.schemas.publico import GenerarLinkOut

router = APIRouter(prefix="/api/clientes", tags=["clientes"])

SessionDep = Annotated[AsyncSession, Depends(authenticated_session)]
ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]
AdminDep = Annotated[TokenClaims, Depends(require_rol("admin"))]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("", response_model=ClienteListOut)
async def listar(
    claims: ClaimsDep,
    session: SessionDep,
    q: Annotated[str | None, Query()] = None,
    modalidad: Annotated[str | None, Query()] = None,
    zona_id: Annotated[uuid.UUID | None, Query()] = None,
    activo: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ClienteListOut:
    items, total = await listar_clientes(
        session,
        empresa_id=claims.empresa_id,
        q=q,
        modalidad=modalidad,
        zona_id=zona_id,
        activo=activo,
        limit=limit,
        offset=offset,
    )
    return ClienteListOut(
        items=[ClienteOut.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{cliente_id}", response_model=ClienteOut)
async def detalle(
    cliente_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> ClienteOut:
    cliente = await obtener_cliente(session, empresa_id=claims.empresa_id, cliente_id=cliente_id)
    return ClienteOut.model_validate(cliente)


@router.post("", response_model=ClienteOut, status_code=201)
async def crear(
    payload: ClienteCreate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ClienteOut:
    cliente = await crear_cliente(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        nombre_completo=payload.nombre_completo,
        telefono=payload.telefono,
        email=payload.email,
        direccion=payload.direccion,
        zona_id=payload.zona_id,
        modalidad=payload.modalidad,
        frecuencia=payload.frecuencia,
        observaciones_permanentes=payload.observaciones_permanentes,
        condicion_pago=payload.condicion_pago,
    )
    return ClienteOut.model_validate(cliente)


@router.patch("/{cliente_id}", response_model=ClienteOut)
async def actualizar(
    cliente_id: uuid.UUID,
    payload: ClienteUpdate,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ClienteOut:
    cambios = payload.model_dump(exclude_unset=True)
    cliente = await actualizar_cliente(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        cliente_id=cliente_id,
        cambios=cambios,
    )
    return ClienteOut.model_validate(cliente)


@router.delete("/{cliente_id}", status_code=204)
async def borrar(
    cliente_id: uuid.UUID,
    admin_claims: AdminDep,
    session: SessionDep,
) -> Response:
    await desactivar_cliente(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        cliente_id=cliente_id,
    )
    return Response(status_code=204)


@router.get("/{cliente_id}/productos-habituales", response_model=ProductosHabitualesOut)
async def listar_productos_habituales(
    cliente_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> ProductosHabitualesOut:
    """Devuelve los productos habituales del cliente."""
    from sqlalchemy import select

    from megarepartos.models.cliente import ProductoHabitual
    from megarepartos.models.producto import Producto

    await obtener_cliente(session, empresa_id=claims.empresa_id, cliente_id=cliente_id)
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
    return ProductosHabitualesOut(
        items=[
            ProductoHabitualItemOut(
                producto_id=r[0], cantidad=r[1], nombre=r[2], es_retornable=r[3]
            )
            for r in rows
        ]
    )


@router.put("/{cliente_id}/productos-habituales", response_model=ProductosHabitualesOut)
async def set_productos_habituales(
    cliente_id: uuid.UUID,
    payload: SetProductosHabitualesIn,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ProductosHabitualesOut:
    """Reemplaza la lista de productos habituales del cliente (admin)."""
    from sqlalchemy import delete, select

    from megarepartos.models.cliente import ProductoHabitual
    from megarepartos.models.producto import Producto

    await obtener_cliente(session, empresa_id=admin_claims.empresa_id, cliente_id=cliente_id)

    # Verificar que todos los productos pertenezcan a la empresa.
    if payload.items:
        producto_ids = [item.producto_id for item in payload.items]
        rows = (
            (
                await session.execute(
                    select(Producto.id).where(
                        Producto.id.in_(producto_ids),
                        Producto.empresa_id == admin_claims.empresa_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        encontrados = set(rows)
        for pid in producto_ids:
            if pid not in encontrados:
                from megarepartos.infra.errors import ApiError, ErrorCode

                raise ApiError(
                    ErrorCode.VALIDACION_SEMANTICA,
                    "Algún producto no existe o no pertenece a la empresa.",
                )

    # Replace strategy: delete + insert.
    await session.execute(delete(ProductoHabitual).where(ProductoHabitual.cliente_id == cliente_id))
    for item in payload.items:
        session.add(
            ProductoHabitual(
                cliente_id=cliente_id,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
            )
        )
    await session.flush()

    return await listar_productos_habituales(cliente_id, admin_claims, session)


@router.post("/{cliente_id}/generar-link", response_model=GenerarLinkOut)
async def generar_link(
    cliente_id: uuid.UUID,
    admin_claims: AdminDep,
    session: SessionDep,
    settings: SettingsDep,
) -> GenerarLinkOut:
    """REQ-LINK-008: genera un link público firmado para un cliente.

    El admin lo pega en WhatsApp manualmente (hasta que la extensión Chrome
    haga envío automático en Sprint 6).
    """
    # Verifica que el cliente exista en la empresa del admin (RLS + filtro).
    await obtener_cliente(session, empresa_id=admin_claims.empresa_id, cliente_id=cliente_id)
    token = sign_link_token(settings, cliente_id=cliente_id)
    return GenerarLinkOut(
        url=f"{settings.frontend_base_url}/c/{token}",
        token=token,
        expira_en_dias=LINK_TOKEN_DEFAULT_TTL_SECONDS // (24 * 60 * 60),
    )
