"""wave1 tenants

Revision ID: wave1_001
Revises:
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave1_001"
down_revision = None
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", _TS, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("custom_domain", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("default_language", sa.String(5), nullable=False),
        sa.Column("default_currency", sa.String(3), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("plan_type", sa.String(20), nullable=False),
        sa.Column("trial_ends_at", _TS, nullable=True),
        sa.Column("suspended_until", _TS, nullable=True),
        sa.Column("suspended_reason", sa.String(500), nullable=True),
        sa.Column("platform_commission_percent", sa.Numeric(5, 4), nullable=True),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("domain"),
        sa.UniqueConstraint("custom_domain"),
    )
    op.create_table(
        "tenant_configs",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("business_name", sa.String(255), nullable=True),
        sa.Column("tax_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("tax_included", sa.Boolean(), nullable=True),
        sa.Column("allow_guest_checkout", sa.Boolean(), nullable=True),
        sa.Column("custom_css", sa.Text(), nullable=True),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )


def downgrade() -> None:
    op.drop_table("tenant_configs")
    op.drop_table("tenants")
