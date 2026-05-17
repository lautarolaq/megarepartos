"""Factories simples para tests. async-friendly (factory-boy no soporta async directo)."""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.models.cliente import Cliente
from megarepartos.models.empresa import Empresa
from megarepartos.models.producto import Producto
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


async def make_cliente(
    session: AsyncSession,
    *,
    empresa: Empresa,
    **overrides: Any,
) -> Cliente:
    """Crea un cliente. **El caller debe haber seteado el tenant context** a la
    empresa (vía `set_tenant_context`) — sino la RLS bloquea el INSERT.
    """
    defaults: dict[str, Any] = {
        "empresa_id": empresa.id,
        "nombre_completo": f"Cliente {uuid.uuid4().hex[:6]}",
        "telefono": f"+5493515{secrets.token_hex(3)}",
        "modalidad": "consulta",
        "condicion_pago": "contado",
        "activo": True,
    }
    defaults.update(overrides)
    cliente = Cliente(**defaults)
    session.add(cliente)
    await session.flush()
    return cliente


async def make_producto(
    session: AsyncSession,
    *,
    empresa: Empresa,
    **overrides: Any,
) -> Producto:
    """Igual que `make_cliente`: requiere tenant context seteado."""
    defaults: dict[str, Any] = {
        "empresa_id": empresa.id,
        "nombre": f"Producto {uuid.uuid4().hex[:6]}",
        "es_retornable": False,
        "activo": True,
        "orden_display": 0,
    }
    defaults.update(overrides)
    producto = Producto(**defaults)
    session.add(producto)
    await session.flush()
    return producto
