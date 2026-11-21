#!/usr/bin/env python3
"""Audit referential integrity and tenant indexes on a migrated schema.

Checks:
  1. Every foreign key points to an existing table.
  2. Every table with a ``tenant_id`` column has an index starting with it
     (required for usable RLS performance at scale).

Usage:
    python scripts/audit_schema.py                # human-readable report
    python scripts/audit_schema.py --check        # exit 1 when issues exist
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]
for part in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API"):
    path = str(ROOT / part)
    if path not in sys.path:
        sys.path.insert(0, path)


def audit(inspector) -> list[str]:
    """Return a list of schema issues; empty means healthy."""
    issues: list[str] = []
    tables = {t for t in inspector.get_table_names() if t != "alembic_version"}

    for table in sorted(tables):
        for fk in inspector.get_foreign_keys(table):
            referred = fk.get("referred_table")
            if referred and referred not in tables:
                issues.append(
                    f"{table}: FK {fk.get('constrained_columns')} -> "
                    f"missing table {referred}"
                )

        columns = {column["name"] for column in inspector.get_columns(table)}
        if "tenant_id" in columns:
            indexes = inspector.get_indexes(table)
            has_tenant_index = any(
                index.get("column_names") and index["column_names"][0] == "tenant_id"
                for index in indexes
            )
            if not has_tenant_index:
                issues.append(f"{table}: tenant_id column has no leading index")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    engine = create_engine(url)
    issues = audit(inspect(engine))
    engine.dispose()

    print(f"schema issues: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    return 1 if args.check and issues else 0


if __name__ == "__main__":
    sys.exit(main())
