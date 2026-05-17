"""Factories simples para tests. async-friendly (factory-boy no soporta async directo)."""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.models.empresa import Empresa
from megarepartos.models.usuario import Usuario


def _unique_email(prefix: str = "test") -> str:
    return f"{prefix}_{secrets.token_hex(4)}@example.com"


async def make_empresa(session: AsyncSession, **overrides: Any) -> Empresa:
    defaults: dict[str, Any] = {
        "nombre": f"Empresa test {uuid.uuid4().hex[:6]}",
        "tipo_negocio": "sodería",
        "estado_suscripcion": "trial",
        "timezone": "America/Argentina/Cordoba",
    }
    defaults.update(overrides)
    empresa = Empresa(**defaults)
    session.add(empresa)
    await session.flush()
    return empresa


async def make_usuario(
    session: AsyncSession,
    *,
    empresa: Empresa | None = None,
    **overrides: Any,
) -> Usuario:
    if empresa is None:
        empresa = await make_empresa(session)
    defaults: dict[str, Any] = {
        "empresa_id": empresa.id,
        "email": _unique_email(),
        "nombre": "Test User",
        "rol": "admin",
        "activo": True,
    }
    defaults.update(overrides)
    usuario = Usuario(**defaults)
    session.add(usuario)
    await session.flush()
    return usuario
