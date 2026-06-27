"""wave4 payments and refunds

Revision ID: wave4_002
Revises: wave4_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave4_002"
down_revision = "wave4_001"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def _tenant_rls(table: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
        )
        """
    )


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("financial_event_id", _PK, nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=False),
        sa.Column("payment_provider", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider_payment_id", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["financial_event_id"], ["financial_events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])
    op.create_table(
        "refunds",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("payment_id", _PK, nullable=False),
        sa.Column("financial_event_id", _PK, nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(
            ["financial_event_id"], ["financial_events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for table in ("payments", "refunds"):
        _tenant_rls(table)


def downgrade() -> None:
    op.drop_table("refunds")
    op.drop_table("payments")
