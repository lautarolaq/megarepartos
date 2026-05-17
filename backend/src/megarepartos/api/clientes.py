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
    HabitualIn,
    actualizar_cliente,
    crear_cliente,
    desactivar_cliente,
    listar_clientes,
    listar_clientes_para_links,
    listar_productos_habituales,
    obtener_cliente,
    registrar_link_generado,
    set_productos_habituales,
)
from megarepartos.infra.auth import (
    LINK_TOKEN_DEFAULT_TTL_SECONDS,
    TokenClaims,
    authenticated_session,
    current_claims,
    require_rol,
    sign_link_token,
)
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.schemas.cliente import (
    ClienteCreate,
    ClienteListOut,
    ClienteOut,
    ClienteUpdate,
    ProductoHabitualItemOut,
    ProductosHabitualesOut,
    SetProductosHabitualesIn,
)
from megarepartos.schemas.publico import (
    GenerarLinkOut,
    GenerarLinksBulkIn,
    GenerarLinksBulkOut,
    LinkBulkItem,
)

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
async def get_productos_habituales(
    cliente_id: uuid.UUID,
    claims: ClaimsDep,
    session: SessionDep,
) -> ProductosHabitualesOut:
    """Devuelve los productos habituales del cliente."""
    items = await listar_productos_habituales(
        session, empresa_id=claims.empresa_id, cliente_id=cliente_id
    )
    return ProductosHabitualesOut(
        items=[
            ProductoHabitualItemOut(
                producto_id=h.producto_id,
                cantidad=h.cantidad,
                nombre=h.nombre,
                es_retornable=h.es_retornable,
            )
            for h in items
        ]
    )


@router.put("/{cliente_id}/productos-habituales", response_model=ProductosHabitualesOut)
async def put_productos_habituales(
    cliente_id: uuid.UUID,
    payload: SetProductosHabitualesIn,
    admin_claims: AdminDep,
    session: SessionDep,
) -> ProductosHabitualesOut:
    """Reemplaza la lista de productos habituales del cliente (admin)."""
    items = await set_productos_habituales(
        session,
        empresa_id=admin_claims.empresa_id,
        cliente_id=cliente_id,
        items=[
            HabitualIn(producto_id=it.producto_id, cantidad=it.cantidad) for it in payload.items
        ],
    )
    return ProductosHabitualesOut(
        items=[
            ProductoHabitualItemOut(
                producto_id=h.producto_id,
                cantidad=h.cantidad,
                nombre=h.nombre,
                es_retornable=h.es_retornable,
            )
            for h in items
        ]
    )


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
    await registrar_link_generado(
        session,
        empresa_id=admin_claims.empresa_id,
        usuario_id=admin_claims.sub,
        cliente_id=cliente_id,
    )
    return GenerarLinkOut(
        url=f"{settings.frontend_base_url}/c/{token}",
        token=token,
        expira_en_dias=LINK_TOKEN_DEFAULT_TTL_SECONDS // (24 * 60 * 60),
    )


@router.post("/generar-links-bulk", response_model=GenerarLinksBulkOut)
async def generar_links_bulk(
    payload: GenerarLinksBulkIn,
    admin_claims: AdminDep,
    session: SessionDep,
    settings: SettingsDep,
) -> GenerarLinksBulkOut:
    """Genera links públicos para todos los clientes activos (opcionalmente
    filtrados por zona). Útil para campañas masivas — el admin ve la lista
    y va abriendo WhatsApp uno a uno.
    """
    zona_id: uuid.UUID | None = None
    if payload.zona_id:
        try:
            zona_id = uuid.UUID(payload.zona_id)
        except ValueError:
            raise ApiError(ErrorCode.VALIDACION_INPUT, "zona_id inválido.") from None

    clientes = await listar_clientes_para_links(
        session, empresa_id=admin_claims.empresa_id, zona_id=zona_id
    )
    items: list[LinkBulkItem] = []
    for c in clientes:
        await registrar_link_generado(
            session,
            empresa_id=admin_claims.empresa_id,
            usuario_id=admin_claims.sub,
            cliente_id=c.id,
        )
        items.append(
            LinkBulkItem(
                cliente_id=str(c.id),
                nombre_completo=c.nombre_completo,
                telefono=c.telefono,
                url=f"{settings.frontend_base_url}/c/{sign_link_token(settings, cliente_id=c.id)}",
            )
        )
    return GenerarLinksBulkOut(items=items)
