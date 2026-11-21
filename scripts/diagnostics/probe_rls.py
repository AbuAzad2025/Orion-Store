"""Probe PostgreSQL RLS status for Orion tables."""

import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _urls():
    load_dotenv()
    urls = []
    for key in ("DATABASE_URL", "TEST_DATABASE_URL", "TEST_DATABASE_URL_ALT"):
        value = os.environ.get(key)
        if value:
            urls.append(value)
    urls += [
        "postgresql://postgres:123@localhost:5432/orion_db",
        "postgresql://postgres:123@localhost:5432/orion_test_db",
    ]
    seen = []
    for u in urls:
        if u not in seen:
            seen.append(u)
    return seen


def main():
    picked = None
    engine = None
    for url in _urls():
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            picked = url
            break
        except Exception:
            if engine:
                try:
                    engine.dispose()
                except Exception:
                    pass
            continue
    if not picked:
        print(
            json.dumps(
                {"error": "No reachable PostgreSQL database found.", "tried": _urls()}
            )
        )
        return

    out = {"database_url": picked, "tables": []}
    with engine.connect() as conn:
        tables = [row[0] for row in conn.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                    """)).fetchall()]
        rels = conn.execute(text("""
                SELECT relname, relrowsecurity
                FROM pg_class
                WHERE relkind = 'r'
                  AND relnamespace = 'public'::regnamespace
                ORDER BY relname
                """)).fetchall()
        rel_map = {row[0]: bool(row[1]) for row in rels}
        policies = conn.execute(text("""
                SELECT tablename
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND policyname = 'tenant_isolation'
                """)).fetchall()
        policy_map = {row[0] for row in policies}

    for name in tables:
        rel = rel_map.get(name, False)
        out["tables"].append(
            {
                "name": name,
                "rls_enabled": rel,
                "tenant_isolation_policy": name in policy_map,
            }
        )
    out["missing_rls"] = [name for name in tables if not rel_map.get(name, False)]
    out["missing_policy"] = sorted(
        {name for name in tables if rel_map.get(name, False) and name not in policy_map}
    )
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
