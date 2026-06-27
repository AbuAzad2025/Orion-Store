"""wave15 launch gaps — cms pages, audit logs

Revision ID: wave15_001
Revises: wave14_001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave15_001"
down_revision = "wave14_001"
branch_labels = None
depends_on = None

_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_TS = sa.DateTime(timezone=True)
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def _tenant_rls(table: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (tenant_id = current_setting('app.tenant_id', true)::bigint)
        """
    )


def upgrade() -> None:
    op.create_table(
        "cms_pages",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_cms_pages_tenant_slug"),
    )
    op.create_index("ix_cms_pages_tenant_id", "cms_pages", ["tenant_id"])
    _tenant_rls("cms_pages")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            ALTER TABLE page_translations
            ADD CONSTRAINT fk_page_translations_cms_page
            FOREIGN KEY (page_id) REFERENCES cms_pages(id) ON DELETE CASCADE
            """
        )

    op.create_table(
        "audit_logs",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=True),
        sa.Column("actor_user_id", _PK, nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("details", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", _TS, server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE page_translations "
            "DROP CONSTRAINT IF EXISTS fk_page_translations_cms_page"
        )
    op.drop_table("audit_logs")
    op.drop_table("cms_pages")
