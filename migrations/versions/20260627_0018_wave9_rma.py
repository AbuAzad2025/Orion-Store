"""wave9 rma tables

Revision ID: wave9_001
Revises: wave8_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave9_001"
down_revision = "wave8_001"
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
        "return_reasons",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_return_reasons_code"),
    )
    op.create_index("ix_return_reasons_tenant_id", "return_reasons", ["tenant_id"])
    _tenant_rls("return_reasons")

    op.create_table(
        "returns",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("return_number", sa.String(50), nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("return_type", sa.String(20), nullable=False),
        sa.Column("reason_id", _PK, nullable=True),
        sa.Column("reason_note", sa.Text(), nullable=True),
        sa.Column("refund_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("refund_method", sa.String(20), nullable=False),
        sa.Column("approved_by", _PK, nullable=True),
        sa.Column("received_at", _TS, nullable=True),
        sa.Column("completed_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reason_id"], ["return_reasons.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("return_number"),
    )
    op.create_index("ix_returns_tenant_id", "returns", ["tenant_id"])
    op.create_index("ix_returns_order_id", "returns", ["order_id"])
    _tenant_rls("returns")

    op.create_table(
        "return_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("return_id", _PK, nullable=False),
        sa.Column("order_item_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(20), nullable=False),
        sa.Column("restock", sa.Boolean(), nullable=False),
        sa.Column("refund_amount", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["return_id"], ["returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["order_item_id"], ["order_items.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("quantity > 0", name="ck_return_items_qty_pos"),
    )
    op.create_index("ix_return_items_return_id", "return_items", ["return_id"])


def downgrade() -> None:
    op.drop_table("return_items")
    if op.get_bind().dialect.name == "postgresql":
        for table in ("returns", "return_reasons"):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("returns")
    op.drop_table("return_reasons")
