"""Domain de autenticación + primer-login.

Función principal: `login_or_create_user`. Toma la identidad verificada de Google
(`GoogleProfile`) y devuelve `(Empresa, Usuario)` listo para emitir JWTs.

REQ-EMP-001..006 implementados acá.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.domain._events import event_recorder
from megarepartos.infra.auth import GoogleProfile
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.models.empresa import Empresa
from megarepartos.models.usuario import Usuario


async def login_or_create_user(
    session: AsyncSession,
    profile: GoogleProfile,
) -> tuple[Empresa, Usuario]:
    """Resuelve `(Empresa, Usuario)` a partir del perfil de Google.

    - Email normalizado a lowercase (REQ-EMP-002).
    - Si el usuario existe e `activo=True`: actualiza `ultima_sesion` (REQ-EMP-003).
    - Si el usuario existe pero `activo=False`: levanta CONFLICTO_ESTADO (REQ-EMP-006).
    - Si no existe: crea Empresa + Usuario nuevo como admin (REQ-EMP-001).
    """
    email = profile.email.strip().lower()

    # Lookup global por email (con lock para evitar carrera en primer-login).
    existing = (
        await session.execute(select(Usuario).where(Usuario.email == email).with_for_update())
    ).scalar_one_or_none()

    if existing is not None:
        if not existing.activo:
            raise ApiError(
                ErrorCode.CONFLICTO_ESTADO,
                "El usuario está desactivado. Contactá al admin de la empresa.",
            )
        existing.ultima_sesion = func.now()
        empresa = (
            await session.execute(select(Empresa).where(Empresa.id == existing.empresa_id))
        ).scalar_one()
        await session.flush()
        return empresa, existing

    # Primer login: crear Empresa + Usuario.
    empresa = Empresa(
        nombre=f"Empresa de {profile.nombre}",
        tipo_negocio="otro",
        estado_suscripcion="trial",
        timezone="America/Argentina/Cordoba",
    )
    session.add(empresa)
    await session.flush()  # asigna empresa.id

    usuario = Usuario(
        empresa_id=empresa.id,
        email=email,
        nombre=profile.nombre,
        rol="admin",
        activo=True,
        ultima_sesion=func.now(),
    )
    session.add(usuario)
    await session.flush()  # asigna usuario.id

    async with event_recorder(
        session,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        entidad_tipo="empresa",
        accion="creada",
    ) as ev:
        ev.entidad_id = empresa.id
        ev.detalles["origen"] = "primer_login_google"
        ev.detalles["google_sub"] = profile.sub

    async with event_recorder(
        session,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        entidad_tipo="usuario",
        accion="creado",
    ) as ev:
        ev.entidad_id = usuario.id
        ev.detalles["email"] = email
        ev.detalles["rol"] = "admin"

    return empresa, usuario


async def obtener_contexto_actual(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    empresa_id: uuid.UUID,
) -> tuple[Empresa, Usuario]:
    """Resuelve `(Empresa, Usuario)` desde los IDs del JWT.

    Levanta `AUTH_INVALID` si:
    - El usuario no existe o está inactivo.
    - La empresa no existe.
    - El usuario no pertenece a la empresa del token (defensa en profundidad
      contra tokens forjados con `empresa_id` ajeno).
    """
    usuario = (
        await session.execute(select(Usuario).where(Usuario.id == usuario_id))
    ).scalar_one_or_none()
    if usuario is None or not usuario.activo:
        raise ApiError(ErrorCode.AUTH_INVALID, "Usuario no existe o está inactivo.")
    empresa = (
        await session.execute(select(Empresa).where(Empresa.id == empresa_id))
    ).scalar_one_or_none()
    if empresa is None or usuario.empresa_id != empresa.id:
        raise ApiError(ErrorCode.AUTH_INVALID, "Empresa no existe o no coincide.")
    return empresa, usuario
