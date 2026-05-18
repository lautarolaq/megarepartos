"""Agrega `broadcast_list_name` a zona.

Campo opcional para que el sodero asocie cada Zona con el nombre de su lista
de difusión en WhatsApp ("Norte Miércoles"). El dashboard usa este hint para
recordarle qué lista pickear cuando manda una campaña broadcast a esa zona.

Revision ID: 0004_zona_broadcast_list_name
Revises: 0003_campana_para_broadcast
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_zona_broadcast_list_name"
down_revision = "0003_campana_para_broadcast"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "zona",
        sa.Column("broadcast_list_name", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("zona", "broadcast_list_name")
