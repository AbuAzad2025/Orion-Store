#!/usr/bin/env python3
"""Audit RLS coverage against tenant-scoped tables.

Reads migration files (source of truth for schema) and reports any table that
has a ``tenant_id`` column but no RLS policy.

Usage:
    python scripts/audit_rls.py            # human-readable report
    python scripts/audit_rls.py --check    # exit 1 when gaps exist (CI)
    python scripts/audit_rls.py --list-missing
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations" / "versions"

_CREATE_TABLE = re.compile(r"op\.create_table\(\s*[\"'](\w+)[\"'](.*?)\n\s*\)", re.S)
_TENANT_COLUMN = re.compile(r"[\"']tenant_id[\"']")
# Baseline migrations emit raw DDL via op.execute("CREATE TABLE ...").
_RAW_CREATE = re.compile(r"CREATE TABLE (\w+) \((.*)")
_RLS_HELPER = re.compile(r"_tenant_rls\(\s*[\"'](\w+)[\"']\s*\)")
_EXPLICIT_ENABLE = re.compile(r"ALTER TABLE (\w+) ENABLE ROW LEVEL SECURITY")
_POLICY = re.compile(r"CREATE POLICY [\w_]+ ON (\w+)")
_TABLE_LIST = re.compile(r"TENANT_TABLES\s*=\s*\((.*?)\)", re.S)
_QUOTED_NAME = re.compile(r"[\"'](\w+)[\"']")


def _scan() -> tuple[set[str], set[str]]:
    tenant_tables: set[str] = set()
    protected: set[str] = set()
    for path in sorted(MIGRATIONS.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for match in _CREATE_TABLE.finditer(source):
            if _TENANT_COLUMN.search(match.group(2)):
                tenant_tables.add(match.group(1))
        for match in _RAW_CREATE.finditer(source):
            if re.search(r"\btenant_id\b", match.group(2)):
                tenant_tables.add(match.group(1))
        protected.update(_RLS_HELPER.findall(source))
        protected.update(_EXPLICIT_ENABLE.findall(source))
        protected.update(_POLICY.findall(source))
        for block in _TABLE_LIST.finditer(source):
            protected.update(_QUOTED_NAME.findall(block.group(1)))
    return tenant_tables, protected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--list-missing", action="store_true")
    args = parser.parse_args()

    tenant_tables, protected = _scan()
    missing = sorted(tenant_tables - protected)

    if args.list_missing:
        for table in missing:
            print(table)
        return 0

    print(f"tables with tenant_id : {len(tenant_tables)}")
    print(f"tables with RLS policy: {len(protected & tenant_tables)}")
    print(f"missing RLS           : {len(missing)}")
    if missing:
        for table in missing:
            print(f"  - {table}")
    return 1 if args.check and missing else 0


if __name__ == "__main__":
    sys.exit(main())
