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
from megarepartos.domain.publico import (
    ProductoRespuesta,
    obtener_info_link,
    registrar_respuesta,
)
from megarepartos.infra.auth import verify_link_token
from megarepartos.infra.db import get_session
from megarepartos.infra.logging import get_logger
from megarepartos.schemas.publico import (
    ClientePublico,
    EmpresaPublica,
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
    """REQ-LINK-005/006: registra la respuesta del cliente como evento_dominio."""
    cliente_id = verify_link_token(settings, token)

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
    )

    _logger.info(
        "publico.respuesta",
        cliente_id=str(cliente_id),
        empresa_id=str(empresa_id),
        accion=payload.accion,
        n_productos=len(productos),
        observacion=payload.observacion,
    )

    await session.commit()
    return {"ok": True}
