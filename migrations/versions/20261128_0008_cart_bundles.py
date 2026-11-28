"""Cart lines may reference a published bundle at its advertised price.

Revision ID: cart_bundles_0008
Revises: cost_price_0007
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "cart_bundles_0008"
down_revision = "cost_price_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.add_column("cart_items", sa.Column("bundle_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_cart_items_bundle_id_product_bundles", "cart_items", "product_bundles",
        ["bundle_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_cart_items_bundle_id", "cart_items", ["bundle_id"])
    op.alter_column("cart_items", "product_id", nullable=True)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column("cart_items", "product_id", nullable=False)
    op.drop_index("ix_cart_items_bundle_id", table_name="cart_items")
    op.drop_constraint("fk_cart_items_bundle_id_product_bundles", "cart_items", type_="foreignkey")
    op.drop_column("cart_items", "bundle_id")
