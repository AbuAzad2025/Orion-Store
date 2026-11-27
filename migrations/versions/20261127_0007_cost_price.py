"""Cost columns are owned by the baseline migration (0001).

Revision ID: cost_price_0007
Revises: strip_store_tokens_0006

This revision is intentionally a no-op: baseline_tables already creates
products.cost_price and order_items.unit_cost. It exists only to keep the
revision chain that shipped with the cost/profit feature. Both directions are
guarded so a downgrade can never drop baseline-owned columns.
"""

from __future__ import annotations

from alembic import op

revision = "cost_price_0007"
down_revision = "strip_store_tokens_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    return


def downgrade() -> None:
    return
