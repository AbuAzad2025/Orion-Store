#!/usr/bin/env python3
"""Post-deployment RLS guard: verify the runtime DB role cannot bypass RLS.

Run against the *application* DATABASE_URL (not the migration/admin URL):

    DATABASE_URL=postgresql://orion_app:***@host:5432/${POSTGRES_DB:-orionstore_db} \
        python scripts/verify_deployment_rls.py --check

    (orionstore_db is the live default; ${POSTGRES_DB:-...} is the configurable
    override shared with docker-compose.prod.yml and backup_db.ps1.)

Checks:
  1. current role is neither superuser nor BYPASSRLS.
  2. current role does not own the tenant tables (owners bypass RLS).
  3. every tenant table has row-level security enabled and a policy.
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg2

TENANT_TABLES_QUERY = """
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN information_schema.columns col
  ON col.table_name = c.relname AND col.table_schema = n.nspname
WHERE n.nspname = 'public' AND col.column_name = 'tenant_id'
  AND c.relkind = 'r'
GROUP BY c.relname
ORDER BY c.relname
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    issues: list[str] = []

    cur.execute(
        "SELECT current_user, r.rolsuper, r.rolbypassrls "
        "FROM pg_roles r WHERE r.rolname = current_user"
    )
    user, is_super, bypass = cur.fetchone()
    print(f"runtime role: {user} (superuser={is_super}, bypassrls={bypass})")
    if is_super or bypass:
        issues.append(
            f"{user} is superuser/BYPASSRLS — RLS is silently disabled in production"
        )

    cur.execute(TENANT_TABLES_QUERY)
    tenant_tables = [row[0] for row in cur.fetchall()]
    print(f"tenant tables: {len(tenant_tables)}")

    for table in tenant_tables:
        cur.execute(
            "SELECT c.relrowsecurity, c.relowner = (SELECT oid FROM pg_roles "
            "WHERE rolname = current_user), "
            "EXISTS (SELECT 1 FROM pg_policies p WHERE p.tablename = c.relname) "
            "FROM pg_class c WHERE c.relname = %s AND c.relnamespace = "
            "(SELECT oid FROM pg_namespace WHERE nspname='public')",
            (table,),
        )
        row = cur.fetchone()
        if not row:
            issues.append(f"{table}: not found")
            continue
        rls, owned, has_policy = row
        if not rls:
            issues.append(f"{table}: RLS disabled")
        if owned:
            issues.append(f"{table}: owned by runtime role — owner bypasses RLS")
        if not has_policy:
            issues.append(f"{table}: no RLS policy")

    conn.close()
    print(f"RLS deployment issues: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    return 1 if args.check and issues else 0


if __name__ == "__main__":
    sys.exit(main())
