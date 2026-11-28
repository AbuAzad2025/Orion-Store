"""Indexes for cart, order-item, bundle and order lookups.

Revision ID: perf_indexes_0010
Revises: schema_drift_parity_0009
"""

from __future__ import annotations

from alembic import op

revision = "perf_indexes_0010"
down_revision = "schema_drift_parity_0009"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_cart_items_cart_id", "cart_items", ["cart_id"]),
    ("ix_order_items_order_id", "order_items", ["order_id"]),
    (
        "ix_product_bundles_tenant_published",
        "product_bundles",
        ["tenant_id", "is_published", "id"],
    ),
    ("ix_product_bundles_tenant_slug", "product_bundles", ["tenant_id", "slug"]),
    (
        "ix_orders_tenant_status_created",
        "orders",
        ["tenant_id", "status", "created_at"],
    ),
    (
        "ix_orders_tenant_paid_created",
        "orders",
        ["tenant_id", "payment_status", "created_at"],
    ),
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
