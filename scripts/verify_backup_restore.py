#!/usr/bin/env python3
"""Backup/restore drill: dump a migrated DB, restore it, compare snapshots.

Requires PostgreSQL client tools (pg_dump/pg_restore) and an admin URL that
can CREATE/DROP databases. Designed for a local/staging drill, never production.

Usage:
    python scripts/verify_backup_restore.py \
        --admin-url postgresql://postgres:postgres@localhost:5433/postgres \
        --pg-bin "C:\\Program Files\\PostgreSQL\\18\\bin"
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg2

SOURCE_DB = "orion_drill_src"
RESTORE_DB = "orion_drill_restored"


def _admin_conn(admin_url: str):
    return psycopg2.connect(admin_url)


def _db_url(admin_url: str, name: str) -> str:
    base = admin_url.rsplit("/", 1)[0]
    return f"{base}/{name}"


def _reset_db(admin_url: str, name: str) -> None:
    conn = _admin_conn(admin_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
            (name,),
        )
        cur.execute(f"DROP DATABASE IF EXISTS {name}")
        cur.execute(f"CREATE DATABASE {name}")
    conn.close()


def _snapshot(url: str) -> tuple[int, int, int, str]:
    conn = psycopg2.connect(url)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
        tables = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM pg_policies WHERE schemaname='public'")
        policies = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM tenants")
        tenants = cur.fetchone()[0]
        cur.execute("SELECT version_num FROM alembic_version")
        version = cur.fetchone()[0]
    conn.close()
    return tables, policies, tenants, version


def _tools(pg_bin: str | None) -> tuple[str, str]:
    dump = shutil.which("pg_dump") or (
        str(Path(pg_bin) / "pg_dump.exe") if pg_bin else ""
    )
    restore = shutil.which("pg_restore") or (
        str(Path(pg_bin) / "pg_restore.exe") if pg_bin else ""
    )
    if not dump or not Path(dump).exists() or not restore or not Path(restore).exists():
        raise SystemExit("pg_dump / pg_restore not found — pass --pg-bin")
    return dump, restore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--admin-url",
        default=os.environ.get(
            "POSTGRES_ADMIN_URL",
            "postgresql://postgres:postgres@localhost:5433/postgres",
        ),
    )
    parser.add_argument("--pg-bin", default=None)
    parser.add_argument("--migrate-command", default="python -m flask db upgrade")
    args = parser.parse_args()

    dump, restore = _tools(args.pg_bin)
    source_url = _db_url(args.admin_url, SOURCE_DB)
    restore_url = _db_url(args.admin_url, RESTORE_DB)

    with tempfile.TemporaryDirectory() as tmp:
        _reset_db(args.admin_url, SOURCE_DB)
        _reset_db(args.admin_url, RESTORE_DB)

        env = os.environ.copy()
        env["DATABASE_URL"] = source_url
        # No shell: the command is provided as an operator-supplied string,
        # split safely into an argument vector.
        subprocess.run(shlex.split(args.migrate_command), check=True, env=env)

        conn = psycopg2.connect(source_url)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (public_id, is_active, version, name, slug, email, "
                "country_code, default_language, default_currency, timezone, status, "
                "plan_type, onboarding_completed) "
                "VALUES (gen_random_uuid(), true, 1, 'Drill', 'drill', 'drill@test.com', "
                "'PS', 'ar', 'ILS', 'Asia/Jerusalem', 'active', 'free', false)"
            )
        conn.commit()
        conn.close()

        dump_file = Path(tmp) / "drill.dump"
        subprocess.run([dump, "-Fc", "-f", str(dump_file), source_url], check=True)
        subprocess.run(
            [
                restore,
                "--no-owner",
                "--no-privileges",
                "-d",
                restore_url,
                str(dump_file),
            ],
            check=True,
        )

        before = _snapshot(source_url)
        after = _snapshot(restore_url)
        print("source :", before)
        print("restored:", after)
        if before != after:
            print("BACKUP/RESTORE MISMATCH", file=sys.stderr)
            return 1

    _reset_db(args.admin_url, SOURCE_DB)
    _reset_db(args.admin_url, RESTORE_DB)
    print("BACKUP_RESTORE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
