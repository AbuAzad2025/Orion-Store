"""wave4 commission ledger

Revision ID: wave4_003
Revises: wave4_002
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave4_003"
down_revision = "wave4_002"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    op.create_table(
        "platform_payment_integrations",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider"),
    )
    op.create_table(
        "platform_commission_ledger",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("financial_event_id", _PK, nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("entry_type", sa.String(30), nullable=False),
        sa.Column("payment_id", _PK, nullable=True),
        sa.Column("order_id", _PK, nullable=True),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_percent", sa.Numeric(5, 4), nullable=False),
        sa.Column("commission_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["financial_event_id"], ["financial_events.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("financial_event_id"),
    )


def downgrade() -> None:
    op.drop_table("platform_commission_ledger")
    op.drop_table("platform_payment_integrations")
