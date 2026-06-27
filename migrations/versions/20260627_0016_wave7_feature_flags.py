"""wave7 feature flags

Revision ID: wave7_002
Revises: wave7_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave7_002"
down_revision = "wave7_001"
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
        "feature_flags",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("default_value", sa.Boolean(), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_feature_flags_category", "feature_flags", ["category"])

    op.create_table(
        "feature_flag_overrides",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("feature_flag_id", _PK, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("value", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("set_by", _PK, nullable=True),
        sa.Column("expires_at", _TS, nullable=True),
        sa.ForeignKeyConstraint(
            ["feature_flag_id"], ["feature_flags.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "feature_flag_id", "tenant_id", name="uq_feature_flag_override_tenant"
        ),
    )
    op.create_index(
        "ix_feature_flag_overrides_tenant_id", "feature_flag_overrides", ["tenant_id"]
    )
    _tenant_rls("feature_flag_overrides")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON feature_flag_overrides")
        op.execute("ALTER TABLE feature_flag_overrides DISABLE ROW LEVEL SECURITY")
    op.drop_table("feature_flag_overrides")
    op.drop_table("feature_flags")
