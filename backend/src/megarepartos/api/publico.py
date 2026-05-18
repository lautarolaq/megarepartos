"""Router `/api/publico/*` — endpoints SIN auth, accedidos por clientes finales
desde el link de WhatsApp.

Reglas:
- NO requiere Bearer token. Valida un link token firmado en la URL.
- NO importa de `models/` (regla CLAUDE.md Backend #6). Las queries van por
  `domain.publico`.
- RLS NO aplica acá — `RESET ROLE` para correr como superuser. La defensa
  es el token firmado + filtro explícito por cliente_id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.domain.clientes import normalizar_telefono
from megarepartos.domain.publico import (
    ProductoRespuesta,
    buscar_cliente_por_telefono,
    obtener_info_link,
    registrar_respuesta,
)
from megarepartos.infra.auth import (
    sign_link_token,
    verify_broadcast_token,
    verify_link_token,
)
from megarepartos.infra.db import get_session
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.infra.logging import get_logger
from megarepartos.schemas.publico import (
    ClientePublico,
    EmpresaPublica,
    IdentificarBroadcastIn,
    IdentificarBroadcastOut,
    LinkPublicoOut,
    ProductoHabitualPublico,
    RespuestaIn,
)

router = APIRouter(prefix="/api/publico", tags=["publico"])

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]

_logger = get_logger(__name__)


@router.get("/c/{token}", response_model=LinkPublicoOut)
async def info_link(
    token: str,
    settings: SettingsDep,
    session: SessionDep,
) -> LinkPublicoOut:
    """REQ-LINK-003/004: devuelve datos del cliente + empresa."""
    cliente_id = verify_link_token(settings, token)

    # RESET ROLE para correr como superuser (no hay tenant context — no
    # sabemos la empresa hasta resolver el cliente).
    await session.execute(text("RESET ROLE"))

    data = await obtener_info_link(session, cliente_id=cliente_id)

    return LinkPublicoOut(
        empresa=EmpresaPublica(nombre=data.empresa_nombre),
        cliente=ClientePublico(
            nombre_completo=data.cliente_nombre_completo,
            telefono=data.cliente_telefono,
        ),
        zona_nombre=data.zona_nombre,
        zona_dia_visita=data.zona_dia_visita,
        productos_habituales=[
            ProductoHabitualPublico(
                producto_id=h.producto_id,
                nombre=h.nombre,
                cantidad_habitual=h.cantidad_habitual,
                es_retornable=h.es_retornable,
            )
            for h in data.productos_habituales
        ],
    )


@router.post("/c/{token}/respuesta")
async def post_respuesta(
    token: str,
    payload: RespuestaIn,
    settings: SettingsDep,
    session: SessionDep,
) -> dict[str, bool]:
    """REQ-LINK-005/006: registra la respuesta del cliente como evento_dominio.

    Si la respuesta viene desde una campaña (broadcast o bulk individual), el
    frontend manda `campana_id` en el body — lo guardamos en el detalles del
    evento para poder filtrar por campaña en el dashboard.
    """
    import uuid as _uuid

    cliente_id = verify_link_token(settings, token)
    campana_id: _uuid.UUID | None = None
    if payload.campana_id:
        try:
            campana_id = _uuid.UUID(payload.campana_id)
        except ValueError:
            campana_id = None  # tolerante: si llega mal, ignoramos en lugar de 400

    await session.execute(text("RESET ROLE"))

    productos = [
        ProductoRespuesta(
            producto_id=p.producto_id,
            cantidad_llenos=p.cantidad_llenos,
            cantidad_vacios=p.cantidad_vacios,
        )
        for p in payload.productos
    ]
    empresa_id = await registrar_respuesta(
        session,
        cliente_id=cliente_id,
        accion=payload.accion,
        productos=productos,
        observacion=payload.observacion,
        campana_id=campana_id,
        zona_mismatch=payload.zona_mismatch,
    )

    _logger.info(
        "publico.respuesta",
        cliente_id=str(cliente_id),
        empresa_id=str(empresa_id),
        accion=payload.accion,
        n_productos=len(productos),
        observacion=payload.observacion,
        campana_id=str(campana_id) if campana_id else None,
    )

    await session.commit()
    return {"ok": True}


# Broadcast -----------------------------------------------------------------
#
# Flujo: el sodero crea una `campana` y firma un broadcast token con su id.
# Mando link → cliente tipea teléfono → backend resuelve cliente vs empresa
# (vía campana) → devuelve token personal de 1h + campana_id. El frontend usa
# el token contra `/c/{token}/respuesta` y manda el campana_id para que la
# respuesta quede taggeada.


@router.post("/b/{token}/identificar", response_model=IdentificarBroadcastOut)
async def identificar_broadcast(
    token: str,
    payload: IdentificarBroadcastIn,
    settings: SettingsDep,
    session: SessionDep,
) -> IdentificarBroadcastOut:
    campana_id = verify_broadcast_token(settings, token)
    telefono_normalizado = normalizar_telefono(payload.telefono)

    await session.execute(text("RESET ROLE"))

    # Resolver empresa + zona de la campaña.
    campana_row = (
        await session.execute(
            text(
                "SELECT empresa_id, destinatarios_origen->>'zona_id' AS zona_id "
                "FROM campana WHERE id = :id"
            ),
            {"id": campana_id},
        )
    ).one_or_none()
    if campana_row is None:
        raise ApiError(
            ErrorCode.RECURSO_NO_ENCONTRADO, "El link no es válido (campaña inexistente)."
        )
    empresa_id = campana_row.empresa_id
    campana_zona_id_str = campana_row.zona_id

    cliente_id = await buscar_cliente_por_telefono(
        session,
        empresa_id=empresa_id,
        telefono=telefono_normalizado,
    )

    data = await obtener_info_link(session, cliente_id=cliente_id)

    # Detectar zona mismatch: si la campaña tiene una zona específica y el
    # cliente pertenece a una zona distinta (o a ninguna), flag para que el
    # frontend pregunte al cliente si confirma igual.
    zona_mismatch = False
    campana_zona_nombre: str | None = None
    if campana_zona_id_str:
        zona_row = (
            await session.execute(
                text(
                    "SELECT z.nombre AS campana_zona_nombre, "
                    "       cl.zona_id::text AS cliente_zona_id "
                    "FROM cliente cl "
                    "LEFT JOIN zona z ON z.id = CAST(:czid AS uuid) "
                    "WHERE cl.id = :cid"
                ),
                {"czid": campana_zona_id_str, "cid": cliente_id},
            )
        ).one_or_none()
        if zona_row:
            campana_zona_nombre = zona_row.campana_zona_nombre
            zona_mismatch = zona_row.cliente_zona_id != campana_zona_id_str

    # Token personal de corta duración (1 hora) — solo para esta sesión.
    cliente_token = sign_link_token(
        settings,
        cliente_id=cliente_id,
        ttl_seconds=60 * 60,
    )

    _logger.info(
        "publico.broadcast.identificar",
        empresa_id=str(empresa_id),
        cliente_id=str(cliente_id),
        campana_id=str(campana_id),
        zona_mismatch=zona_mismatch,
    )

    return IdentificarBroadcastOut(
        cliente_token=cliente_token,
        campana_id=str(campana_id),
        zona_mismatch=zona_mismatch,
        campana_zona_nombre=campana_zona_nombre,
        cliente_zona_nombre=data.zona_nombre,
        info=LinkPublicoOut(
            empresa=EmpresaPublica(nombre=data.empresa_nombre),
            cliente=ClientePublico(
                nombre_completo=data.cliente_nombre_completo,
                telefono=data.cliente_telefono,
            ),
            zona_nombre=data.zona_nombre,
            zona_dia_visita=data.zona_dia_visita,
            productos_habituales=[
                ProductoHabitualPublico(
                    producto_id=h.producto_id,
                    nombre=h.nombre,
                    cantidad_habitual=h.cantidad_habitual,
                    es_retornable=h.es_retornable,
                )
                for h in data.productos_habituales
            ],
        ),
    )
