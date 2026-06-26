"""wave2 products

Revision ID: wave2_003
Revises: wave2_002
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave2_003"
down_revision = "wave2_002"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", _TS, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.String(500), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("compare_at_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("category_id", _PK, nullable=True),
        sa.Column("brand_id", _PK, nullable=True),
        sa.CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        sa.CheckConstraint("quantity >= 0", name="ck_products_qty_nonneg"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("slug", "tenant_id", name="uq_products_slug"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON products")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON products
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
            )
            """
        )


def downgrade() -> None:
    op.drop_table("products")
