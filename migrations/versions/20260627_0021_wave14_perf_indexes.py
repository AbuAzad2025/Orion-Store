"""wave14 storefront performance indexes

Revision ID: wave14_001
Revises: wave9_003
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op

revision = "wave14_001"
down_revision = "wave9_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_tenant_published_active
        ON products (tenant_id, created_at DESC)
        WHERE deleted_at IS NULL AND is_published = TRUE
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_categories_tenant_active
        ON categories (tenant_id, sort_order, name)
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_categories_tenant_active")
    op.execute("DROP INDEX IF EXISTS ix_products_tenant_published_active")
