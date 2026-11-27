"""Add product cost price and order-item cost snapshot for profit reports.

Revision ID: cost_price_0007
Revises: strip_store_tokens_0006
"""

from __future__ import annotations

from alembic import op

revision = "cost_price_0007"
down_revision = "strip_store_tokens_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS cost_price "
        "NUMERIC(10, 2) NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS unit_cost "
        "NUMERIC(10, 2) NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS unit_cost")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS cost_price")
