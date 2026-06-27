"""wave8 paypal bnpl tables

Revision ID: wave8_001
Revises: wave7_002
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave8_001"
down_revision = "wave7_002"
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
        "bnpl_providers",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("merchant_id", sa.String(255), nullable=True),
        sa.Column("api_credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", name="uq_bnpl_providers_tenant"),
    )
    op.create_index("ix_bnpl_providers_tenant_id", "bnpl_providers", ["tenant_id"])
    _tenant_rls("bnpl_providers")

    op.create_table(
        "bnpl_transactions",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("external_transaction_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("installment_plan", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "external_transaction_id", name="uq_bnpl_transactions_external"
        ),
    )
    op.create_index("ix_bnpl_transactions_tenant_id", "bnpl_transactions", ["tenant_id"])
    op.create_index("ix_bnpl_transactions_order_id", "bnpl_transactions", ["order_id"])
    _tenant_rls("bnpl_transactions")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("bnpl_transactions", "bnpl_providers"):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("bnpl_transactions")
    op.drop_table("bnpl_providers")
