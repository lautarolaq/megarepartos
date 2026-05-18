"""Campana usable sin template_mensaje.

Permite usar la tabla `campana` para registrar envíos broadcast y bulk
individual SIN tener que crear un row de `template_mensaje` por cada uno.
El mensaje + zona + tipo van en `destinatarios_origen` JSONB.

Revision ID: 0003_campana_para_broadcast
Revises: 0002_rls_business_tables
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_campana_para_broadcast"
down_revision = "0002_rls_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # template_mensaje_id pasa a ser opcional. Las campañas nuevas (broadcast,
    # bulk individual) no usan plantillas guardadas — snapshotean el mensaje
    # en destinatarios_origen JSONB.
    op.alter_column(
        "campana",
        "template_mensaje_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # En downgrade no podemos volver a NOT NULL si hay rows con NULL — lo
    # dejamos como NULLABLE incluso en downgrade para no romper. Si querés
    # estricto, primero llená esas filas a mano.
    op.alter_column(
        "campana",
        "template_mensaje_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )
