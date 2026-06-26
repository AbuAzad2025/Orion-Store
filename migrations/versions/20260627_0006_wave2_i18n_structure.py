"""wave2 i18n structure (schema only)

Revision ID: wave2_004
Revises: wave2_003
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave2_004"
down_revision = "wave2_003"
branch_labels = None
depends_on = None

_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_TS = sa.DateTime(timezone=True)
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    op.create_table(
        "product_translations",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("product_id", _PK, nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "locale", name="uq_product_trans_locale"),
    )
    op.create_table(
        "category_translations",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("category_id", _PK, nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "locale", name="uq_category_trans_locale"),
    )
    op.create_table(
        "page_translations",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("page_id", _PK, nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "locale", name="uq_page_trans_locale"),
    )
    op.create_table(
        "translation_glossary",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=True),
        sa.Column("source_locale", sa.String(5), nullable=False),
        sa.Column("target_locale", sa.String(5), nullable=False),
        sa.Column("source_term", sa.String(255), nullable=False),
        sa.Column("target_term", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "currency_rates",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("updated_at", _TS, server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "base_currency", "target_currency", name="uq_currency_rates_pair"
        ),
    )


def downgrade() -> None:
    op.drop_table("currency_rates")
    op.drop_table("translation_glossary")
    op.drop_table("page_translations")
    op.drop_table("category_translations")
    op.drop_table("product_translations")
