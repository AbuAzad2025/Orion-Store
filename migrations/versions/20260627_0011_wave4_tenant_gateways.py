"""wave4 tenant gateways

Revision ID: wave4_004
Revises: wave4_003
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave4_004"
down_revision = "wave4_003"
branch_labels = None
depends_on = None

_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "tenant_payment_gateways",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_sandbox", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("connected_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", name="uq_tenant_gateway"),
    )
    op.create_index(
        "ix_tenant_gateways_tenant", "tenant_payment_gateways", ["tenant_id"]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE tenant_payment_gateways ENABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON tenant_payment_gateways")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON tenant_payment_gateways
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
            )
            """
        )


def downgrade() -> None:
    op.drop_table("tenant_payment_gateways")
