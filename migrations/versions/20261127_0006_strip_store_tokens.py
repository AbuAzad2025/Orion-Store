"""Strip embedded store tokens from persisted image URLs.

Revision ID: strip_store_tokens_0006
Revises: force_rls_0004

Store tokens now expire. Image URLs must never be persisted with a token;
renderers add a fresh one per request. This migration cleans any legacy rows.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "strip_store_tokens_0006"
down_revision = "force_rls_0004"
branch_labels = None
depends_on = None

TABLES = ("products", "product_bundles", "categories")


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        has_column = bind.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t "
                "AND column_name = 'image_url'"
            ),
            {"t": table},
        ).scalar()
        if not has_column:
            continue
        rows = bind.execute(
            text(
                f"SELECT id, image_url FROM {table} "
                "WHERE image_url LIKE '%?store=%'"
            )
        ).fetchall()
        for row_id, url in rows:
            bind.execute(
                text(f"UPDATE {table} SET image_url = :u WHERE id = :i"),
                {"u": str(url).split("?", 1)[0], "i": row_id},
            )
        if rows:
            print(f"STRIPPED {table} {len(rows)}")


def downgrade() -> None:
    # Tokens are intentionally not restored — they were expiring credentials.
    pass
