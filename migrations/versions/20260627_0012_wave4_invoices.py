"""wave4 invoices

Revision ID: wave4_004b
Revises: wave4_004
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "wave4_004b"
down_revision = "wave4_004"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)
_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_NOW = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    op.create_table(
        "tenant_document_templates",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "invoices",
        sa.Column("id", _PK, autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", _PK, nullable=False),
        sa.Column("order_id", _PK, nullable=False),
        sa.Column("financial_event_id", _PK, nullable=True),
        sa.Column("payment_id", _PK, nullable=True),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("platform_footer_applied", sa.Boolean(), nullable=False),
        sa.Column("issued_at", _TS, server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["financial_event_id"], ["financial_events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE invoices ENABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON invoices")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON invoices
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
            )
            """
        )


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("tenant_document_templates")
