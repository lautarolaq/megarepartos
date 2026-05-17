"""Tests de aislamiento multi-tenant. Verifican que RLS de Postgres bloquea
acceso a datos de otra empresa.

Cubren REQ-MT-001..008. La regla CLAUDE.md Tests #5 exige aislamiento en cada
endpoint nuevo — esta suite es la base sobre la que se construyen esos tests.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.infra.db import set_tenant_context
from megarepartos.models.cliente import Cliente
from megarepartos.models.template import TemplateMensaje
from tests.factories import make_cliente, make_empresa, make_producto, make_usuario

# ---- REQ-MT-001 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-001")
async def test_REQ_MT_001_rls_habilitado_en_tablas_de_negocio(
    db_session: AsyncSession,
) -> None:
    """Verifica que cada tabla esperada tiene RLS habilitado **y forzado**."""
    expected = (
        "cliente",
        "producto",
        "envase",
        "zona",
        "campana",
        "template_mensaje",
        "template_formulario",
        "evento_dominio",
        "token_extension",
        "sheet_referencia",
        "producto_habitual",
        "mensaje_enviado",
        "respuesta_link",
        "confirmacion_pedido",
    )
    rows = (
        await db_session.execute(
            text(
                """
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = ANY(:names)
                """
            ),
            {"names": list(expected)},
        )
    ).all()
    statuses = {r[0]: (r[1], r[2]) for r in rows}
    for table in expected:
        assert statuses.get(table) == (True, True), (
            f"{table}: RLS no habilitado o no forzado ({statuses.get(table)!r})"
        )


# ---- REQ-MT-002 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-002")
async def test_REQ_MT_002_set_tenant_context_setea_session_vars(
    db_session: AsyncSession,
) -> None:
    """`set_tenant_context` deja `app.empresa_id` y `app.usuario_id` legibles."""
    empresa_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    await set_tenant_context(db_session, empresa_id=empresa_id, usuario_id=usuario_id)

    val_emp = (
        await db_session.execute(text("SELECT current_setting('app.empresa_id', true)"))
    ).scalar_one()
    val_usr = (
        await db_session.execute(text("SELECT current_setting('app.usuario_id', true)"))
    ).scalar_one()
    assert val_emp == str(empresa_id)
    assert val_usr == str(usuario_id)


# ---- REQ-MT-003 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-003")
async def test_REQ_MT_003_select_cliente_solo_devuelve_empresa_actual(
    db_session: AsyncSession,
) -> None:
    """Crea 2 clientes en empresa A y 1 en B. Bajo contexto A, solo se ven los 2 de A."""
    empresa_a = await make_empresa(db_session, nombre="A")
    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_a = await make_usuario(db_session, empresa=empresa_a)
    usuario_b = await make_usuario(db_session, empresa=empresa_b)

    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    await make_cliente(db_session, empresa=empresa_a, nombre_completo="Ana de A")
    await make_cliente(db_session, empresa=empresa_a, nombre_completo="Beto de A")

    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    await make_cliente(db_session, empresa=empresa_b, nombre_completo="Carla de B")

    # Volver a contexto A y leer clientes: solo los 2 de A.
    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    nombres = sorted((await db_session.execute(select(Cliente.nombre_completo))).scalars().all())
    assert nombres == ["Ana de A", "Beto de A"]


# ---- REQ-MT-004 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-004")
async def test_REQ_MT_004_insert_cliente_con_empresa_ajena_falla(
    db_session: AsyncSession,
) -> None:
    """Bajo contexto A, intentar INSERT cliente con empresa_id=B falla por WITH CHECK."""
    empresa_a = await make_empresa(db_session, nombre="A")
    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_a = await make_usuario(db_session, empresa=empresa_a)

    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    with pytest.raises(DBAPIError):
        # Forzamos empresa_id=B: la policy WITH CHECK lo rechaza.
        await make_cliente(db_session, empresa=empresa_b)


# ---- REQ-MT-005 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-005")
async def test_REQ_MT_005_update_cliente_ajeno_es_invisible(
    db_session: AsyncSession,
) -> None:
    """Un UPDATE sobre un cliente de B desde contexto A afecta 0 rows (RLS oculta)."""
    empresa_a = await make_empresa(db_session, nombre="A")
    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_a = await make_usuario(db_session, empresa=empresa_a)
    usuario_b = await make_usuario(db_session, empresa=empresa_b)

    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    cliente_b = await make_cliente(db_session, empresa=empresa_b, nombre_completo="Original")

    # Cambiar contexto a A y tratar de updatear el id de B. Usamos SQL crudo
    # para evitar que el identity map del ORM sincronice el objeto local
    # antes de que la query llegue a Postgres.
    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    result = await db_session.execute(
        text("UPDATE cliente SET nombre_completo = 'Hackeado' WHERE id = :id"),
        {"id": cliente_b.id},
    )
    assert result.rowcount == 0

    # Volver a B y confirmar via SQL crudo que el nombre original sigue
    # (evitamos identity map del ORM).
    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    nombre_en_db = (
        await db_session.execute(
            text("SELECT nombre_completo FROM cliente WHERE id = :id"),
            {"id": cliente_b.id},
        )
    ).scalar_one()
    assert nombre_en_db == "Original"


# ---- REQ-MT-006 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-006")
async def test_REQ_MT_006_sin_contexto_devuelve_cero_rows(
    db_session: AsyncSession,
) -> None:
    """Sin `app.empresa_id` seteado, las queries devuelven 0 rows (fail-closed)."""
    empresa = await make_empresa(db_session)
    usuario = await make_usuario(db_session, empresa=empresa)
    await set_tenant_context(db_session, empresa_id=empresa.id, usuario_id=usuario.id)
    await make_cliente(db_session, empresa=empresa)
    await make_producto(db_session, empresa=empresa)

    # Resetear los session vars a vacío.
    await db_session.execute(text("SELECT set_config('app.empresa_id', '', true)"))

    clientes = (await db_session.execute(select(Cliente))).scalars().all()
    assert clientes == []


# ---- REQ-MT-007 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-007")
async def test_REQ_MT_007_templates_preset_visibles_desde_cualquier_empresa(
    db_session: AsyncSession,
) -> None:
    """Templates con `empresa_id IS NULL` (presets) los ven todas las empresas."""
    empresa_a = await make_empresa(db_session, nombre="A")
    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_a = await make_usuario(db_session, empresa=empresa_a)
    usuario_b = await make_usuario(db_session, empresa=empresa_b)

    # Insertar el preset como superuser (RLS no aplica). En prod los presets
    # se crean vía migración o admin endpoint con rol elevado.
    preset_id = uuid.uuid4()
    await db_session.execute(text("RESET ROLE"))
    await db_session.execute(
        text(
            """
            INSERT INTO template_mensaje (id, empresa_id, nombre, tipo, contenido, es_preset, activo)
            VALUES (:id, NULL, 'Preset Consulta', 'consulta', 'Hola {nombre}', true, true)
            """
        ),
        {"id": preset_id},
    )
    # Volver al rol de la app — desde acá RLS aplica.
    await db_session.execute(text("SET LOCAL ROLE megarepartos_app"))

    # Empresa A ve el preset.
    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    found_a = (
        await db_session.execute(select(TemplateMensaje).where(TemplateMensaje.id == preset_id))
    ).scalar_one_or_none()
    assert found_a is not None

    # Empresa B también.
    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    found_b = (
        await db_session.execute(select(TemplateMensaje).where(TemplateMensaje.id == preset_id))
    ).scalar_one_or_none()
    assert found_b is not None


# ---- REQ-MT-008 ----


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-008")
async def test_REQ_MT_008_tablas_indirectas_heredan_filtro_via_exists(
    db_session: AsyncSession,
) -> None:
    """`producto_habitual` no tiene empresa_id; hereda el filtro vía cliente."""
    from megarepartos.models.cliente import ProductoHabitual

    empresa_a = await make_empresa(db_session, nombre="A")
    empresa_b = await make_empresa(db_session, nombre="B")
    usuario_a = await make_usuario(db_session, empresa=empresa_a)
    usuario_b = await make_usuario(db_session, empresa=empresa_b)

    # Seed: empresa A con cliente + producto + producto_habitual.
    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    cli_a = await make_cliente(db_session, empresa=empresa_a)
    prod_a = await make_producto(db_session, empresa=empresa_a)
    db_session.add(ProductoHabitual(cliente_id=cli_a.id, producto_id=prod_a.id, cantidad=2))
    await db_session.flush()

    # Seed: empresa B con su propio cliente + producto + habitual.
    await set_tenant_context(db_session, empresa_id=empresa_b.id, usuario_id=usuario_b.id)
    cli_b = await make_cliente(db_session, empresa=empresa_b)
    prod_b = await make_producto(db_session, empresa=empresa_b)
    db_session.add(ProductoHabitual(cliente_id=cli_b.id, producto_id=prod_b.id, cantidad=5))
    await db_session.flush()

    # Desde contexto A, solo se ve la habitualidad de cli_a.
    await set_tenant_context(db_session, empresa_id=empresa_a.id, usuario_id=usuario_a.id)
    rows = (await db_session.execute(select(ProductoHabitual))).scalars().all()
    assert len(rows) == 1
    assert rows[0].cliente_id == cli_a.id
