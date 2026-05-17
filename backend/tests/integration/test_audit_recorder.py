"""Tests del `event_recorder` (TASK-005 / REQ-AUD-004 / 005)."""

from __future__ import annotations

import pytest

from megarepartos.domain._events import event_recorder
from megarepartos.infra.errors import ApiError, ErrorCode


@pytest.mark.integration
@pytest.mark.req("REQ-AUD-004")
async def test_REQ_AUD_004_funciona_fuera_de_request(db_session) -> None:
    """Sin contextvars (sin HTTP request), el recorder persiste igual con
    ip/user_agent en NULL."""
    from sqlalchemy import select, text

    from megarepartos.models.evento import EventoDominio
    from tests.factories import make_empresa, make_usuario

    empresa = await make_empresa(db_session)
    usuario = await make_usuario(db_session, empresa=empresa)
    await db_session.execute(
        text("SELECT set_config('app.empresa_id', :e, true)"), {"e": str(empresa.id)}
    )
    await db_session.execute(
        text("SELECT set_config('app.usuario_id', :u, true)"), {"u": str(usuario.id)}
    )

    async with event_recorder(
        db_session,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        entidad_tipo="empresa",
        accion="creada",
    ) as ev:
        ev.entidad_id = empresa.id

    evento = (
        (
            await db_session.execute(
                select(EventoDominio)
                .where(EventoDominio.empresa_id == empresa.id)
                .order_by(EventoDominio.fecha.desc())
            )
        )
        .scalars()
        .first()
    )
    assert evento is not None
    assert evento.ip_origen is None
    assert evento.user_agent is None
    # request_id no se incluye porque la contextvar está en None.
    assert "request_id" not in evento.detalles_jsonb


@pytest.mark.unit
@pytest.mark.req("REQ-AUD-005")
async def test_REQ_AUD_005_falla_sin_empresa_id() -> None:
    """`event_recorder` requiere `empresa_id` no-None."""
    with pytest.raises(ApiError) as exc:
        async with event_recorder(
            session=None,  # type: ignore[arg-type]
            empresa_id=None,  # type: ignore[arg-type]
            usuario_id=None,
            entidad_tipo="x",
            accion="y",
        ):
            pass
    assert exc.value.code == ErrorCode.INTERNO
