"""`event_recorder` — wraps writes para que generen `evento_dominio`.

Regla CLAUDE.md Backend #2: "Toda operación de escritura usa `event_recorder`".

En TASK-001/002 este módulo es un stub: registra el evento en `evento_dominio` con
información mínima. TASK-005 lo completa con diff de campos, request_id,
ip_origen, user_agent.

Uso:

```python
async with event_recorder(
    session,
    empresa_id=empresa.id,
    usuario_id=usuario.id,
    entidad_tipo="usuario",
    accion="creado",
) as ev:
    ev.detalles["email"] = email
    # ... operaciones de escritura ...
```

Al salir del context manager, se persiste el `EventoDominio`. Si la operación
falla y se hace rollback, el evento también se rollbackea (vive en la misma
transacción).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.models.evento import EventoDominio


@dataclass(slots=True)
class _EventoCtx:
    """Handle expuesto dentro del `async with event_recorder(...)` para que el
    caller pueda llenar `detalles` antes de que se persista.
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

    No hace `commit`: queda en la transacción del caller. Si la transacción
    se rollbackea, el evento también.
    """
    ctx = _EventoCtx()
    try:
        yield ctx
    finally:
        evento = EventoDominio(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            entidad_tipo=entidad_tipo,
            entidad_id=ctx.entidad_id,
            accion=accion,
            detalles_jsonb=ctx.detalles,
        )
        session.add(evento)
        # Flush para que se asigne el id pero sin commit (el caller controla).
        await session.flush()
