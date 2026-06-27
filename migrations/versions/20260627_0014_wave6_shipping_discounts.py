"""wave6 shipping and vouchers

Revision ID: wave6_001
Revises: gap5_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave6_001"
down_revision = "gap5_001"
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
        "shipping_methods",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", _TS, nullable=True),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("base_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("free_shipping_threshold", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_order_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_order_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimated_days_min", sa.Integer(), nullable=True),
        sa.Column("estimated_days_max", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "tenant_id", name="uq_shipping_methods_code_tenant"),
    )
    op.create_index("ix_shipping_methods_tenant_id", "shipping_methods", ["tenant_id"])

    op.create_table(
        "shipping_zones",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", _TS, nullable=True),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("countries", sa.JSON(), nullable=True),
        sa.Column("regions", sa.JSON(), nullable=True),
        sa.Column("postal_codes", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipping_zones_tenant_id", "shipping_zones", ["tenant_id"])

    op.create_table(
        "shipping_rates",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("shipping_method_id", _PK, nullable=False),
        sa.Column("shipping_zone_id", _PK, nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["shipping_method_id"], ["shipping_methods.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["shipping_zone_id"], ["shipping_zones.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipping_rates_tenant_id", "shipping_rates", ["tenant_id"])

    op.create_table(
        "vouchers",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", _TS, nullable=True),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_order_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_discount_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("start_date", _TS, nullable=True),
        sa.Column("end_date", _TS, nullable=True),
        sa.Column("is_free_shipping", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "tenant_id", name="uq_vouchers_code_tenant"),
    )
    op.create_index("ix_vouchers_tenant_id", "vouchers", ["tenant_id"])

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("shipping_method_code", sa.String(50), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "discount_amount",
                sa.Numeric(10, 2),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("discount_code", sa.String(100), nullable=True))

    for table in (
        "shipping_methods",
        "shipping_zones",
        "shipping_rates",
        "vouchers",
    ):
        _tenant_rls(table)


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("discount_code")
        batch_op.drop_column("discount_amount")
        batch_op.drop_column("shipping_method_code")

    op.drop_table("vouchers")
    op.drop_table("shipping_rates")
    op.drop_table("shipping_zones")
    op.drop_table("shipping_methods")
