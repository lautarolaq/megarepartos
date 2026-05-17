"""Schema inicial — sección 5 del SPEC.

Crea todas las tablas del modelo de datos en una sola migración (regla TASK-000:
no partir en varias migraciones). Las próximas migraciones agregarán columnas /
tablas a medida que se avanza con cada TASK.

Revision ID: 0001_schema_inicial
Revises:
Create Date: 2026-05-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_schema_inicial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- plan ----
    op.create_table(
        "plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=64), nullable=False),
        sa.Column("precio_mensual", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "limites_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan")),
        sa.UniqueConstraint("nombre", name=op.f("uq_plan_nombre")),
    )

    # ---- empresa ----
    op.create_table(
        "empresa",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("tipo_negocio", sa.String(length=32), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "estado_suscripcion",
            sa.String(length=16),
            server_default="trial",
            nullable=False,
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fecha_cancelacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("direccion_deposito", sa.String(length=512), nullable=True),
        sa.Column(
            "coordenadas_deposito_lat", sa.Numeric(precision=10, scale=7), nullable=True
        ),
        sa.Column(
            "coordenadas_deposito_lng", sa.Numeric(precision=10, scale=7), nullable=True
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="America/Argentina/Cordoba",
            nullable=False,
        ),
        sa.Column(
            "config_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plan.id"],
            name=op.f("fk_empresa_plan_id_plan"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_empresa")),
    )

    # ---- usuario ----
    op.create_table(
        "usuario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column(
            "rol", sa.String(length=16), server_default="operador", nullable=False
        ),
        sa.Column("google_oauth_token", sa.String(length=2048), nullable=True),
        sa.Column(
            "google_oauth_scopes",
            postgresql.ARRAY(sa.String(length=128)),
            nullable=True,
        ),
        sa.Column("ultima_sesion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_usuario_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("empresa_id", "email", name="uq_usuario_empresa_email"),
    )
    op.create_index(
        op.f("ix_usuario_empresa_id"), "usuario", ["empresa_id"], unique=False
    )

    # ---- envase ----
    op.create_table(
        "envase",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column(
            "valor_referencial", sa.Numeric(precision=12, scale=2), nullable=True
        ),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_envase_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_envase")),
    )
    op.create_index(
        op.f("ix_envase_empresa_id"), "envase", ["empresa_id"], unique=False
    )

    # ---- producto ----
    op.create_table(
        "producto",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("descripcion", sa.String(length=1024), nullable=True),
        sa.Column(
            "precio_unitario_default", sa.Numeric(precision=12, scale=2), nullable=True
        ),
        sa.Column(
            "es_retornable", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("envase_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("orden_display", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_producto_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["envase_id"],
            ["envase.id"],
            name=op.f("fk_producto_envase_id_envase"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_producto")),
    )
    op.create_index(
        op.f("ix_producto_empresa_id"), "producto", ["empresa_id"], unique=False
    )

    # ---- zona ----
    op.create_table(
        "zona",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("dia_visita", sa.String(length=16), nullable=True),
        sa.Column("camioneta_asignada", sa.String(length=128), nullable=True),
        sa.Column("color_display", sa.String(length=16), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_zona_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zona")),
    )
    op.create_index(op.f("ix_zona_empresa_id"), "zona", ["empresa_id"], unique=False)

    # ---- cliente ----
    op.create_table(
        "cliente",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre_completo", sa.String(length=255), nullable=False),
        sa.Column("telefono", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("direccion", sa.String(length=512), nullable=True),
        sa.Column("coordenadas_lat", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("coordenadas_lng", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("zona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "modalidad",
            sa.String(length=16),
            server_default="consulta",
            nullable=False,
        ),
        sa.Column("frecuencia", sa.String(length=16), nullable=True),
        sa.Column("observaciones_permanentes", sa.String(length=2048), nullable=True),
        # FK lógica a lista_precios — tabla aún no existe (feature futura).
        sa.Column("lista_precios_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "condicion_pago",
            sa.String(length=16),
            server_default="contado",
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_modificacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ultima_consulta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultima_visita", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_cliente_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["zona_id"],
            ["zona.id"],
            name=op.f("fk_cliente_zona_id_zona"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cliente")),
    )
    op.create_index(
        op.f("ix_cliente_empresa_id"), "cliente", ["empresa_id"], unique=False
    )
    op.create_index(
        op.f("ix_cliente_telefono"), "cliente", ["telefono"], unique=False
    )

    # ---- producto_habitual ----
    op.create_table(
        "producto_habitual",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("producto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name=op.f("fk_producto_habitual_cliente_id_cliente"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["producto.id"],
            name=op.f("fk_producto_habitual_producto_id_producto"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_producto_habitual")),
    )
    op.create_index(
        op.f("ix_producto_habitual_cliente_id"),
        "producto_habitual",
        ["cliente_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_producto_habitual_producto_id"),
        "producto_habitual",
        ["producto_id"],
        unique=False,
    )

    # ---- template_mensaje ----
    op.create_table(
        "template_mensaje",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("es_preset", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_template_mensaje_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_template_mensaje")),
    )
    op.create_index(
        op.f("ix_template_mensaje_empresa_id"),
        "template_mensaje",
        ["empresa_id"],
        unique=False,
    )

    # ---- template_formulario ----
    op.create_table(
        "template_formulario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column(
            "config_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("es_preset", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_template_formulario_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_template_formulario")),
    )
    op.create_index(
        op.f("ix_template_formulario_empresa_id"),
        "template_formulario",
        ["empresa_id"],
        unique=False,
    )

    # ---- campana ----
    op.create_table(
        "campana",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_creador_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column(
            "template_mensaje_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "template_formulario_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "estado", sa.String(length=16), server_default="borrador", nullable=False
        ),
        sa.Column("fecha_programada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_envio_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_envio_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "destinatarios_origen",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "estadisticas",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_campana_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_creador_id"],
            ["usuario.id"],
            name=op.f("fk_campana_usuario_creador_id_usuario"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_mensaje_id"],
            ["template_mensaje.id"],
            name=op.f("fk_campana_template_mensaje_id_template_mensaje"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_formulario_id"],
            ["template_formulario.id"],
            name=op.f("fk_campana_template_formulario_id_template_formulario"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campana")),
    )
    op.create_index(
        op.f("ix_campana_empresa_id"), "campana", ["empresa_id"], unique=False
    )

    # ---- mensaje_enviado ----
    op.create_table(
        "mensaje_enviado",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campana_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("destinatario_telefono", sa.String(length=32), nullable=False),
        sa.Column("destinatario_nombre", sa.String(length=255), nullable=False),
        sa.Column("contenido_final", sa.Text(), nullable=False),
        sa.Column("link_unico", sa.String(length=512), nullable=True),
        sa.Column("token_link", sa.String(length=255), nullable=True),
        sa.Column(
            "estado", sa.String(length=16), server_default="pendiente", nullable=False
        ),
        sa.Column("fecha_envio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_lectura", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detalle", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(
            ["campana_id"],
            ["campana.id"],
            name=op.f("fk_mensaje_enviado_campana_id_campana"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name=op.f("fk_mensaje_enviado_cliente_id_cliente"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mensaje_enviado")),
        sa.UniqueConstraint("token_link", name=op.f("uq_mensaje_enviado_token_link")),
    )
    op.create_index(
        op.f("ix_mensaje_enviado_campana_id"),
        "mensaje_enviado",
        ["campana_id"],
        unique=False,
    )

    # ---- respuesta_link ----
    op.create_table(
        "respuesta_link",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mensaje_enviado_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_usado", sa.String(length=255), nullable=False),
        sa.Column(
            "fecha_acceso",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip_acceso", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "accion",
            sa.String(length=16),
            server_default="en_proceso",
            nullable=False,
        ),
        sa.Column(
            "datos_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("fecha_accion", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["mensaje_enviado_id"],
            ["mensaje_enviado.id"],
            name=op.f("fk_respuesta_link_mensaje_enviado_id_mensaje_enviado"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_respuesta_link")),
    )
    op.create_index(
        op.f("ix_respuesta_link_mensaje_enviado_id"),
        "respuesta_link",
        ["mensaje_enviado_id"],
        unique=False,
    )

    # ---- confirmacion_pedido ----
    op.create_table(
        "confirmacion_pedido",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("respuesta_link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_propuesta", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "productos_solicitados",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "envases_a_devolver",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("observacion_cliente", sa.String(length=2048), nullable=True),
        sa.ForeignKeyConstraint(
            ["respuesta_link_id"],
            ["respuesta_link.id"],
            name=op.f("fk_confirmacion_pedido_respuesta_link_id_respuesta_link"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name=op.f("fk_confirmacion_pedido_cliente_id_cliente"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_confirmacion_pedido")),
    )
    op.create_index(
        op.f("ix_confirmacion_pedido_respuesta_link_id"),
        "confirmacion_pedido",
        ["respuesta_link_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_confirmacion_pedido_cliente_id"),
        "confirmacion_pedido",
        ["cliente_id"],
        unique=False,
    )

    # ---- evento_dominio ----
    op.create_table(
        "evento_dominio",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entidad_tipo", sa.String(length=32), nullable=False),
        sa.Column("entidad_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accion", sa.String(length=32), nullable=False),
        sa.Column(
            "detalles_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip_origen", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_evento_dominio_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_evento_dominio_usuario_id_usuario"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evento_dominio")),
    )
    op.create_index(
        op.f("ix_evento_dominio_empresa_id"),
        "evento_dominio",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evento_dominio_entidad_tipo"),
        "evento_dominio",
        ["entidad_tipo"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evento_dominio_entidad_id"),
        "evento_dominio",
        ["entidad_id"],
        unique=False,
    )

    # ---- token_extension ----
    op.create_table(
        "token_extension",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_ultima_validacion", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("revocado", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "detalles_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_token_extension_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_token_extension_usuario_id_usuario"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_token_extension")),
        sa.UniqueConstraint("token", name=op.f("uq_token_extension_token")),
    )
    op.create_index(
        op.f("ix_token_extension_empresa_id"),
        "token_extension",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_token_extension_usuario_id"),
        "token_extension",
        ["usuario_id"],
        unique=False,
    )

    # ---- sheet_referencia ----
    op.create_table(
        "sheet_referencia",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("google_sheet_id", sa.String(length=128), nullable=False),
        sa.Column("google_sheet_url", sa.String(length=1024), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fecha_ultima_lectura", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "estado", sa.String(length=16), server_default="activo", nullable=False
        ),
        sa.Column("campana_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresa.id"],
            name=op.f("fk_sheet_referencia_empresa_id_empresa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campana_id"],
            ["campana.id"],
            name=op.f("fk_sheet_referencia_campana_id_campana"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sheet_referencia")),
    )
    op.create_index(
        op.f("ix_sheet_referencia_empresa_id"),
        "sheet_referencia",
        ["empresa_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop en orden inverso para respetar dependencias.
    op.drop_index(op.f("ix_sheet_referencia_empresa_id"), table_name="sheet_referencia")
    op.drop_table("sheet_referencia")

    op.drop_index(op.f("ix_token_extension_usuario_id"), table_name="token_extension")
    op.drop_index(op.f("ix_token_extension_empresa_id"), table_name="token_extension")
    op.drop_table("token_extension")

    op.drop_index(op.f("ix_evento_dominio_entidad_id"), table_name="evento_dominio")
    op.drop_index(op.f("ix_evento_dominio_entidad_tipo"), table_name="evento_dominio")
    op.drop_index(op.f("ix_evento_dominio_empresa_id"), table_name="evento_dominio")
    op.drop_table("evento_dominio")

    op.drop_index(
        op.f("ix_confirmacion_pedido_cliente_id"), table_name="confirmacion_pedido"
    )
    op.drop_index(
        op.f("ix_confirmacion_pedido_respuesta_link_id"),
        table_name="confirmacion_pedido",
    )
    op.drop_table("confirmacion_pedido")

    op.drop_index(
        op.f("ix_respuesta_link_mensaje_enviado_id"), table_name="respuesta_link"
    )
    op.drop_table("respuesta_link")

    op.drop_index(op.f("ix_mensaje_enviado_campana_id"), table_name="mensaje_enviado")
    op.drop_table("mensaje_enviado")

    op.drop_index(op.f("ix_campana_empresa_id"), table_name="campana")
    op.drop_table("campana")

    op.drop_index(
        op.f("ix_template_formulario_empresa_id"), table_name="template_formulario"
    )
    op.drop_table("template_formulario")

    op.drop_index(
        op.f("ix_template_mensaje_empresa_id"), table_name="template_mensaje"
    )
    op.drop_table("template_mensaje")

    op.drop_index(
        op.f("ix_producto_habitual_producto_id"), table_name="producto_habitual"
    )
    op.drop_index(
        op.f("ix_producto_habitual_cliente_id"), table_name="producto_habitual"
    )
    op.drop_table("producto_habitual")

    op.drop_index(op.f("ix_cliente_telefono"), table_name="cliente")
    op.drop_index(op.f("ix_cliente_empresa_id"), table_name="cliente")
    op.drop_table("cliente")

    op.drop_index(op.f("ix_zona_empresa_id"), table_name="zona")
    op.drop_table("zona")

    op.drop_index(op.f("ix_producto_empresa_id"), table_name="producto")
    op.drop_table("producto")

    op.drop_index(op.f("ix_envase_empresa_id"), table_name="envase")
    op.drop_table("envase")

    op.drop_index(op.f("ix_usuario_empresa_id"), table_name="usuario")
    op.drop_table("usuario")

    op.drop_table("empresa")

    op.drop_table("plan")
