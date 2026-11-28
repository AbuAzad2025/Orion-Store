"""Reconcile four model/baseline column drifts.

Revision ID: schema_drift_parity_0009
Revises: cart_bundles_0008

Widen two URL columns to 512 and guarantee two server DEFAULT 0 values.
Safe to re-run: each DDL change is skipped when the catalog already matches.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "schema_drift_parity_0009"
down_revision = "cart_bundles_0008"
branch_labels = None
depends_on = None

URL_COLUMNS = (("tenants", "logo_url"), ("product_bundles", "image_url"))
COST_COLUMNS = (("products", "cost_price"), ("order_items", "unit_cost"))


def _catalog_value(column_name: str, table: str, column: str):
    bind = op.get_bind()
    return bind.execute(
        text(
            f"SELECT {column_name} FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t "
            "AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).scalar()


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, column in URL_COLUMNS:
        if _catalog_value("character_maximum_length", table, column) == 512:
            continue
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=500),
            type_=sa.String(length=512),
            existing_nullable=True,
        )
    for table, column in COST_COLUMNS:
        if _catalog_value("column_default", table, column) is not None:
            continue
        op.alter_column(
            table,
            column,
            existing_type=sa.Numeric(10, 2),
            server_default=sa.text("0"),
            existing_nullable=False,
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # URL widths and DEFAULT 0 are baseline-owned (0001 now creates 512 and
    # DEFAULT 0). Narrowing here would break parity with a fresh DB and could
    # truncate stored values, so the downgrade is intentionally a no-op.
