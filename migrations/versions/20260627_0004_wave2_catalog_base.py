"""wave2 locales and catalog base

Revision ID: wave2_002
Revises: wave2_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave2_002"
down_revision = "wave2_001"
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
        "locales",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("code", sa.String(5), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("direction", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "categories",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", _TS, nullable=True),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.String(500), nullable=True),
        sa.Column("parent_id", _PK, nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(500), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("show_in_menu", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "tenant_id", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_tenant_id", "categories", ["tenant_id"])
    op.create_table(
        "brands",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", _TS, nullable=True),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "tenant_id", name="uq_brands_slug"),
    )
    op.create_index("ix_brands_tenant_id", "brands", ["tenant_id"])
    _tenant_rls("categories")
    _tenant_rls("brands")


def downgrade() -> None:
    op.drop_table("brands")
    op.drop_table("categories")
    op.drop_table("locales")
