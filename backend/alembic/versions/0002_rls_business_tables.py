"""RLS (Row-Level Security) sobre tablas de negocio.

Habilita + FORCE Row-Level Security en todas las tablas de negocio (las que
tienen `empresa_id` directo o lo heredan vía FK). Cada policy filtra por
`current_setting('app.empresa_id', true)` que la app setea por request vía
`authenticated_session` (`infra/auth.py`).

NO se aplica RLS sobre `empresa`, `usuario` ni `plan` — estas tablas se acceden
por el auth flow / config compartida.

Revision ID: 0002_rls_business_tables
Revises: 0001_schema_inicial
Create Date: 2026-05-17

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_rls_business_tables"
down_revision: str | Sequence[str] | None = "0001_schema_inicial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tablas con columna `empresa_id` directa. Policy USING/WITH CHECK simple.
DIRECT_TABLES: tuple[str, ...] = (
    "cliente",
    "producto",
    "envase",
    "zona",
    "campana",
    "evento_dominio",
    "token_extension",
    "sheet_referencia",
)

# Tablas con `empresa_id` nullable y semántica de "preset compartido".
NULLABLE_EMPRESA_TABLES: tuple[str, ...] = (
    "template_mensaje",
    "template_formulario",
)

# Tablas indirectas: derivan empresa via FK al padre.
# (tabla, columna_fk, tabla_padre, columna_padre)
INDIRECT_POLICIES: tuple[tuple[str, str, str, str], ...] = (
    ("producto_habitual", "cliente_id", "cliente", "id"),
    ("mensaje_enviado", "campana_id", "campana", "id"),
    ("respuesta_link", "mensaje_enviado_id", "mensaje_enviado", "id"),
    ("confirmacion_pedido", "cliente_id", "cliente", "id"),
)


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    # FORCE: aplica también al owner. Necesario porque la app y la migración
    # usan el mismo rol (sin FORCE el owner bypassa RLS).
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")


def _disable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")


def _create_direct_policy(table: str) -> None:
    """Policy clásica: empresa_id::text = current_setting('app.empresa_id', true)."""
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        AS PERMISSIVE
        FOR ALL
        USING (empresa_id::text = current_setting('app.empresa_id', true))
        WITH CHECK (empresa_id::text = current_setting('app.empresa_id', true));
        """
    )


def _create_nullable_empresa_policy(table: str) -> None:
    """Policy para tablas con `empresa_id` nullable (presets).

    SELECT: rows con empresa_id NULL o que matchean.
    INSERT/UPDATE: empresa_id debe matchear (no permitimos crear presets vía app).
    """
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        AS PERMISSIVE
        FOR ALL
        USING (
            empresa_id IS NULL
            OR empresa_id::text = current_setting('app.empresa_id', true)
        )
        WITH CHECK (
            empresa_id::text = current_setting('app.empresa_id', true)
        );
        """
    )


def _create_indirect_policy(
    table: str, fk_col: str, parent_table: str, parent_col: str
) -> None:
    """Policy para tablas sin empresa_id propio.

    USING / WITH CHECK chequean que el padre matchee. Notar que el SELECT
    interno también pasa por RLS del padre (que ya filtra por empresa).
    """
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        AS PERMISSIVE
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM {parent_table} p
                WHERE p.{parent_col} = {table}.{fk_col}
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM {parent_table} p
                WHERE p.{parent_col} = {table}.{fk_col}
            )
        );
        """
    )


def _create_app_role() -> None:
    """Crea el rol `megarepartos_app` (no-superuser) que la app usará en runtime.

    Postgres bypassa RLS para superusers — el rol del docker-compose / Neon es
    superuser y por eso necesitamos un rol separado para que las policies se
    apliquen. En runtime, la app conectará como superuser pero hará
    `SET ROLE megarepartos_app` al iniciar cada request (vía `set_tenant_context`).

    Idempotente: si el rol ya existe, no hace nada.
    """
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'megarepartos_app') THEN
                CREATE ROLE megarepartos_app
                    NOSUPERUSER
                    NOINHERIT
                    NOCREATEDB
                    NOCREATEROLE;
            END IF;
        END
        $$;
        """
    )
    # Grants. Idempotentes — Postgres no falla si ya están.
    op.execute("GRANT USAGE ON SCHEMA public TO megarepartos_app;")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO megarepartos_app;"
    )
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO megarepartos_app;")
    # Future tables creadas por migraciones siguientes heredan los mismos grants.
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO megarepartos_app;
        """
    )
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT USAGE ON SEQUENCES TO megarepartos_app;
        """
    )


def upgrade() -> None:
    _create_app_role()

    for table in DIRECT_TABLES:
        _enable_rls(table)
        _create_direct_policy(table)

    for table in NULLABLE_EMPRESA_TABLES:
        _enable_rls(table)
        _create_nullable_empresa_policy(table)

    for table, fk, parent, parent_col in INDIRECT_POLICIES:
        _enable_rls(table)
        _create_indirect_policy(table, fk, parent, parent_col)


def downgrade() -> None:
    # Orden inverso para evitar problemas con dependencias entre policies
    # (las indirectas dependen de las directas vía EXISTS).
    for table, _, _, _ in reversed(INDIRECT_POLICIES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        _disable_rls(table)

    for table in reversed(NULLABLE_EMPRESA_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        _disable_rls(table)

    for table in reversed(DIRECT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        _disable_rls(table)
