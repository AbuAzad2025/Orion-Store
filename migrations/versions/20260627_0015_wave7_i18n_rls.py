"""wave7 i18n RLS and indexes

Revision ID: wave7_001
Revises: wave6_001
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op

revision = "wave7_001"
down_revision = "wave6_001"
branch_labels = None
depends_on = None


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
    op.create_index(
        "ix_product_translations_tenant_locale",
        "product_translations",
        ["tenant_id", "locale"],
    )
    op.create_index(
        "ix_category_translations_tenant_locale",
        "category_translations",
        ["tenant_id", "locale"],
    )
    _tenant_rls("product_translations")
    _tenant_rls("category_translations")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON product_translations")
        op.execute("ALTER TABLE product_translations DISABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON category_translations")
        op.execute("ALTER TABLE category_translations DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_category_translations_tenant_locale", "category_translations")
    op.drop_index("ix_product_translations_tenant_locale", "product_translations")
