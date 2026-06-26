"""wave2 platform settings

Revision ID: wave2_001
Revises: wave1_002
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave2_001"
down_revision = "wave1_002"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("platform_name", sa.String(100), nullable=False),
        sa.Column("platform_logo_url", sa.String(500), nullable=True),
        sa.Column("platform_logo_dark_url", sa.String(500), nullable=True),
        sa.Column("footer_html", sa.Text(), nullable=False),
        sa.Column("owner_name", sa.String(200), nullable=False),
        sa.Column("owner_phone", sa.String(50), nullable=False),
        sa.Column("owner_phone_intl", sa.String(50), nullable=False),
        sa.Column("owner_email", sa.String(255), nullable=True),
        sa.Column("default_commission_percent", sa.Numeric(5, 4), nullable=False),
        sa.Column("singleton", sa.CHAR(1), nullable=False),
        sa.Column("valuepayment_enabled", sa.Boolean(), nullable=False),
        sa.Column("valuepayment_config", sa.JSON(), nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.CheckConstraint("singleton = '1'", name="ck_platform_settings_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
