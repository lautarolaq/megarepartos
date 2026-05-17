"""Router `/api/publico/*` — endpoints SIN auth, accedidos por clientes finales
desde el link de WhatsApp.

Reglas:
- NO requiere Bearer token. Valida un link token firmado en la URL.
- NO importa de `models/` (regla CLAUDE.md Backend #6). Las queries van por
  domain functions que devuelven schemas.
- RLS NO aplica acá — la query se hace con session sin tenant context. La
  defensa es el token firmado + filtro explícito por cliente_id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.config import Settings, get_settings
from megarepartos.infra.auth import verify_link_token
from megarepartos.infra.db import get_session
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.infra.logging import get_logger
from megarepartos.models.cliente import Cliente, ProductoHabitual
from megarepartos.models.empresa import Empresa
from megarepartos.models.producto import Producto
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
    """REQ-LINK-003/004: devuelve datos del cliente + empresa.

    Defensa: el token firmado garantiza acceso al cliente_id correcto.
    La query corre como superuser (bypassa RLS) — RLS no tiene sentido
    acá porque no hay tenant context (somos pre-tenant).
    """
    cliente_id = verify_link_token(settings, token)

    # RESET ROLE para correr la query como superuser (bypass RLS).
    # Necesario porque el role megarepartos_app no ve nada sin
    # app.empresa_id seteado, pero acá NO sabemos la empresa hasta
    # resolver el cliente.
    await session.execute(text("RESET ROLE"))

    cliente = (
        await session.execute(select(Cliente).where(Cliente.id == cliente_id))
    ).scalar_one_or_none()
    if cliente is None or not cliente.activo:
        raise ApiError(ErrorCode.RECURSO_NO_ENCONTRADO, "El link no es válido.")

    empresa = (
        await session.execute(select(Empresa).where(Empresa.id == cliente.empresa_id))
    ).scalar_one()

    # Productos habituales del cliente — orden alfabético.
    habituales_rows = (
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

    productos_habituales = [
        ProductoHabitualPublico(
            producto_id=str(row[0]),
            cantidad_habitual=row[1],
            nombre=row[2],
            es_retornable=row[3],
        )
        for row in habituales_rows
    ]

    return LinkPublicoOut(
        empresa=EmpresaPublica.model_validate(empresa),
        cliente=ClientePublico.model_validate(cliente),
        productos_habituales=productos_habituales,
    )


@router.post("/c/{token}/respuesta")
async def registrar_respuesta(
    token: str,
    payload: RespuestaIn,
    settings: SettingsDep,
    session: SessionDep,
) -> dict[str, bool]:
    """REQ-LINK-005: registra la respuesta del cliente.

    Por ahora loggea — la persistencia en `respuesta_link` requiere
    `mensaje_enviado_id` que viene de Sprint 5 (campañas).
    """
    cliente_id = verify_link_token(settings, token)

    await session.execute(text("RESET ROLE"))
    row = (
        await session.execute(
            text("SELECT empresa_id FROM cliente WHERE id = :id AND activo = true"),
            {"id": cliente_id},
        )
    ).scalar_one_or_none()
    if row is None:
        raise ApiError(ErrorCode.RECURSO_NO_ENCONTRADO, "El link no es válido.")

    _logger.info(
        "publico.respuesta",
        cliente_id=str(cliente_id),
        empresa_id=str(row),
        accion=payload.accion,
        productos=[p.model_dump() for p in payload.productos],
        observacion=payload.observacion,
    )

    return {"ok": True}
