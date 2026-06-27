"""wave9 b2b tables

Revision ID: wave9_002
Revises: wave9_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave9_002"
down_revision = "wave9_001"
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
        "price_lists",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_lists_tenant_id", "price_lists", ["tenant_id"])
    _tenant_rls("price_lists")

    op.create_table(
        "customer_groups",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("price_list_id", _PK, nullable=True),
        sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False),
        sa.Column("is_wholesale", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["price_list_id"], ["price_lists.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_customer_groups_code"),
    )
    op.create_index("ix_customer_groups_tenant_id", "customer_groups", ["tenant_id"])
    _tenant_rls("customer_groups")

    op.create_table(
        "customer_group_members",
        sa.Column("customer_group_id", _PK, nullable=False),
        sa.Column("user_id", _PK, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_group_id"], ["customer_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("customer_group_id", "user_id"),
    )
    _tenant_rls("customer_group_members")

    op.create_table(
        "price_list_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("price_list_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["price_list_id"], ["price_lists.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "price_list_id",
            "product_id",
            "min_quantity",
            name="uq_price_list_items",
        ),
    )

    op.create_table(
        "quotes",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("quote_number", sa.String(50), nullable=False),
        sa.Column("user_id", _PK, nullable=True),
        sa.Column("customer_group_id", _PK, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("valid_until", _TS, nullable=True),
        sa.Column("converted_order_id", _PK, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["customer_group_id"], ["customer_groups.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["converted_order_id"], ["orders.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_number"),
    )
    op.create_index("ix_quotes_tenant_id", "quotes", ["tenant_id"])
    _tenant_rls("quotes")

    op.create_table(
        "quote_items",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("quote_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("quote_items")
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "quotes",
            "customer_group_members",
            "customer_groups",
            "price_lists",
        ):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("quotes")
    op.drop_table("price_list_items")
    op.drop_table("customer_group_members")
    op.drop_table("customer_groups")
    op.drop_table("price_lists")
