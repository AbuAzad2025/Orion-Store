"""Gap closure — invoice rendered_html and PDF artifact columns.

Revision ID: gap5_001
Revises: wave4_004b
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "gap5_001"
down_revision = "wave4_004b"
branch_labels = None
depends_on = None

_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rendered_html", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("pdf_artifact_path", sa.String(500), nullable=True)
        )
        batch_op.add_column(sa.Column("document_template_id", _PK, nullable=True))
        batch_op.create_foreign_key(
            "fk_invoices_document_template_id",
            "tenant_document_templates",
            ["document_template_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_invoices_document_template_id", type_="foreignkey"
        )
        batch_op.drop_column("document_template_id")
        batch_op.drop_column("pdf_artifact_path")
        batch_op.drop_column("rendered_html")
