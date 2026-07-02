"""Add rollout_percent to feature_flags (fixes v2_all_001 bug)."""

from alembic import op
import sqlalchemy as sa

revision = "v2_all_002"
down_revision = "v2_all_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feature_flags",
        sa.Column("rollout_percent", sa.Integer(), server_default=sa.text("100"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("feature_flags", "rollout_percent")
