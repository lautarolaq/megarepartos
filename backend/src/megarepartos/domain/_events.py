"""`event_recorder` — wraps writes para que generen `evento_dominio`.

Regla CLAUDE.md Backend #2: "Toda operación de escritura usa `event_recorder`".

Captura automáticamente `request_id`, `ip_origen` y `user_agent` desde las
contextvars que setea `AuditContextMiddleware`. Fuera de un request HTTP
(crons, tests directos), esos campos quedan en NULL.

Uso:

```python
async with event_recorder(
    session,
    empresa_id=empresa.id,
    usuario_id=usuario.id,
    entidad_tipo="producto",
    accion="creado",
) as ev:
    ev.entidad_id = producto.id
    ev.detalles["nombre"] = producto.nombre
```

Al salir del context manager, se persiste el `EventoDominio`. Si la operación
falla y la transacción se rollbackea, el evento también.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.infra.audit_context import (
    current_ip_origen,
    current_request_id,
    current_user_agent,
)
from megarepartos.infra.errors import ApiError, ErrorCode
from megarepartos.models.evento import EventoDominio


@dataclass(slots=True)
class _EventoCtx:
    """Handle expuesto dentro del `async with event_recorder(...)` para que el
    caller pueda llenar `entidad_id` y `detalles` antes de que se persista.
    """

    entidad_id: uuid.UUID | None = None
    detalles: dict[str, Any] = field(default_factory=dict)


@asynccontextmanager
async def event_recorder(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID | None,
    entidad_tipo: str,
    accion: str,
) -> AsyncIterator[_EventoCtx]:
    """Context manager que persiste un `EventoDominio` al salir.

    No hace `commit`: queda en la transacción del caller.
    """
    # Defensa runtime aún con tipo no-None — defensa contra callers en tests
    # o tipo erróneo. Mypy ve este branch como inalcanzable; convertimos
    # `empresa_id` a `Any` localmente para que mypy no marque "unreachable".
    if not empresa_id:
        raise ApiError(ErrorCode.INTERNO, "event_recorder requiere empresa_id (REQ-AUD-005).")

    ctx = _EventoCtx()
    try:
        yield ctx
    finally:
        # Inyectar contexto del request si está disponible.
        request_id = current_request_id.get()
        if request_id is not None:
            ctx.detalles.setdefault("request_id", request_id)

        evento = EventoDominio(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            entidad_tipo=entidad_tipo,
            entidad_id=ctx.entidad_id,
            accion=accion,
            detalles_jsonb=ctx.detalles,
            ip_origen=current_ip_origen.get(),
            user_agent=current_user_agent.get(),
        )
        session.add(evento)
        await session.flush()
