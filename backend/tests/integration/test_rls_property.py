"""Property-based test del invariante de RLS (REQ-MT-010).

Para cualquier configuración válida de empresas/clientes, una query desde el
contexto de empresa X devuelve **exactamente** los clientes de X. Ni uno más,
ni uno menos.

Hypothesis genera múltiples combinaciones (cantidades, nombres, etc.) y verifica
el invariante. Si encuentra un caso que rompe, lo reporta.
"""

from __future__ import annotations

import secrets
import uuid

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.infra.db import set_tenant_context
from megarepartos.models.cliente import Cliente
from tests.factories import make_cliente, make_empresa, make_usuario

# Datos generados por hypothesis para cada empresa.
# Cada elemento es una lista de nombres (uno por cliente a crear).
nombre_strategy = (
    st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N"),  # letras + números, sin emoji/control
            whitelist_characters=" ",
        ),
        min_size=1,
        max_size=30,
    )
    .map(str.strip)
    .filter(lambda s: len(s) >= 1)
)

empresa_data_strategy = st.lists(nombre_strategy, min_size=0, max_size=10)

# Lista de empresas, cada una con su lista de nombres de clientes.
escenario_strategy = st.lists(empresa_data_strategy, min_size=2, max_size=5)


@pytest.mark.integration
@pytest.mark.isolation
@pytest.mark.req("REQ-MT-010")
@given(escenario=escenario_strategy)
@settings(
    max_examples=30,
    deadline=None,  # Postgres roundtrips → no aplicar deadline.
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
async def test_REQ_MT_010_property_aislamiento_cliente_holds_para_n_empresas(
    db_session: AsyncSession,
    escenario: list[list[str]],
) -> None:
    """Invariante: SELECT desde contexto X devuelve exactamente los clientes de X."""
    # Setup: crear empresas + usuario admin + clientes según el escenario.
    empresas_y_ids: list[tuple[uuid.UUID, uuid.UUID, set[uuid.UUID]]] = []
    for idx, nombres in enumerate(escenario):
        emp = await make_empresa(db_session, nombre=f"E{idx}-{secrets.token_hex(2)}")
        usr = await make_usuario(db_session, empresa=emp)
        await set_tenant_context(db_session, empresa_id=emp.id, usuario_id=usr.id)
        ids_de_esta_empresa: set[uuid.UUID] = set()
        for nombre in nombres:
            cli = await make_cliente(db_session, empresa=emp, nombre_completo=nombre)
            ids_de_esta_empresa.add(cli.id)
        empresas_y_ids.append((emp.id, usr.id, ids_de_esta_empresa))

    # Verificación: para cada empresa, su SELECT devuelve EXACTAMENTE sus IDs.
    for empresa_id, usuario_id, ids_esperados in empresas_y_ids:
        await set_tenant_context(db_session, empresa_id=empresa_id, usuario_id=usuario_id)
        rows = (await db_session.execute(select(Cliente.id))).scalars().all()
        ids_observados = set(rows)
        assert ids_observados == ids_esperados, (
            f"Empresa {empresa_id}: esperados={len(ids_esperados)}, "
            f"observados={len(ids_observados)}, "
            f"leaks={ids_observados - ids_esperados}, "
            f"missing={ids_esperados - ids_observados}"
        )
