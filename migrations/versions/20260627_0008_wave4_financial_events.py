"""wave4 financial events

Revision ID: wave4_001
Revises: wave3_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave4_001"
down_revision = "wave3_001"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    op.create_table(
        "financial_events",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("source_entity", sa.String(30), nullable=False),
        sa.Column("source_id", _PK, nullable=False),
        sa.Column("gateway_id", _PK, nullable=True),
        sa.Column("platform_gateway_id", _PK, nullable=True),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("commission_applied", sa.Boolean(), nullable=False),
        sa.Column("commission_percent", sa.Numeric(5, 4), nullable=True),
        sa.Column("commission_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("commission_ledger_id", _PK, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("completed_at", _TS, nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_fin_events_amount_pos"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_financial_events_tenant_id", "financial_events", ["tenant_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE financial_events ENABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON financial_events")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON financial_events
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
            )
            """
        )


def downgrade() -> None:
    op.drop_table("financial_events")
