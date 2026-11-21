"""Read-only Alembic/model schema check plus v2 FK validation.

This gate never writes files: schema drift is detected with Alembic's
``compare_metadata`` instead of Alembic's file-writing autogenerate
revision API, which used to create a revision file on every run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _component in (
    "02-CORE",
    "03-MODELS",
    "04-SERVICES",
    "05-API",
    "06-STOREFRONT",
    "07-ADMIN",
):
    sys.path.insert(0, str(ROOT / _component))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENCRYPTION_KEY"] = "test-key"
os.environ["USE_SQLITE_TESTS"] = "1"

# Known v1 tables (pre-v2).
V1_TABLES = {
    "tenants",
    "tenant_configs",
    "users",
    "roles",
    "brands",
    "categories",
    "products",
    "alembic_version",
    "carts",
    "cart_items",
    "orders",
    "order_items",
    "order_events",
    "payments",
    "refunds",
    "financial_events",
    "commission_ledger",
    "invoices",
    "platform_settings",
    "tenant_gateways",
    "shipping_zones",
    "shipping_rates",
    "vouchers",
    "voucher_redemptions",
    "locales",
    "translations",
    "glossaries",
    "pages",
    "feature_flags",
    "feature_flag_overrides",
    "price_lists",
    "price_list_items",
    "customer_groups",
    "customer_group_members",
    "return_requests",
    "return_items",
    "warehouses",
    "inventory_levels",
    "fulfillments",
    "fulfillment_items",
    "b2b_quotes",
    "b2b_quote_items",
    "store_accounts",
    "store_addresses",
}


def _schema_diffs(connection, metadata) -> list[str]:
    """Describe model-vs-database drift without emitting a revision file."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    context = MigrationContext.configure(connection)
    return [str(diff) for diff in compare_metadata(context, metadata)]


def _baseline_model_diffs(metadata) -> list[str]:
    """Compare model tables/columns with the baseline migration's CREATE TABLEs.

    Reading the actual migration file is what makes this a real gate: comparing
    a metadata-built database back to the same metadata is always a no-op.
    """
    import re

    baseline = ROOT / "migrations/versions/20261119_0001_baseline_tables.py"
    if not baseline.exists():
        return [f"baseline migration not found: {baseline}"]
    text = baseline.read_text(encoding="utf-8")
    created: dict[str, str] = {}
    for table_name, ddl in re.findall(
        r"CREATE TABLE (\w+) \((.*?)\\n\)", text, re.DOTALL
    ):
        created[table_name] = ddl

    diffs: list[str] = []
    for table_name, table in metadata.tables.items():
        ddl = created.get(table_name)
        if ddl is None:
            diffs.append(f"table {table_name}: missing from baseline migration")
            continue
        for column in table.columns:
            # Migration DDL has literal \t escapes, so use the type after the
            # column name as the anchor instead of a word boundary.
            if not re.search(
                rf"{re.escape(column.name)}\s+(?:BIGSERIAL|SERIAL|BIGINT|SMALLINT|VARCHAR|CHAR|TEXT|NUMERIC|DECIMAL|BOOLEAN|UUID|INTEGER|DATE|TIMESTAMP|DATETIME|JSON)",
                ddl,
            ):
                diffs.append(
                    f"table {table_name}: column {column.name} missing from baseline"
                )
    return diffs


def main() -> int:
    from sqlalchemy import inspect

    from orion.app import create_app
    from orion.extensions import db

    app = create_app("testing")
    issues: list[str] = []

    with app.app_context():
        # Build the reference schema from the models in an in-memory database.
        db.create_all()

        inspector = inspect(db.engine)
        all_tables = set(inspector.get_table_names())
        v2_tables = all_tables - V1_TABLES - {"alembic_version"}
        print(f"Total tables in DB: {len(all_tables)}")
        print(f"v2 tables detected: {len(v2_tables)}")
        print()

        for t in sorted(v2_tables):
            cols = {c["name"]: c for c in inspector.get_columns(t)}
            fks = inspector.get_foreign_keys(t)
            print(f"  {t}:")
            print(f"      columns: {list(cols.keys())}")
            print(f"      FKs ({len(fks)}):")
            for fk in fks:
                ref = f"{fk['referred_table']}.{fk['referred_columns']}"
                constrained = fk["constrained_columns"]
                print(f"        {constrained} -> {ref}")
                if fk["referred_table"] not in all_tables:
                    issues.append(
                        f"  {t}: FK {constrained} -> {ref} — referred table MISSING!"
                    )
            print()

        print(
            "--- Read-only model vs baseline migration comparison (no files written) ---"
        )
        diffs = _baseline_model_diffs(db.metadata)
        if diffs:
            issues.append(f"model/schema drift: {len(diffs)} change(s) detected")
            issues.extend(f"  {diff}" for diff in diffs)
        else:
            print("No schema drift detected — no revision is needed.")

        if "tenant_feature_flag_overrides" in all_tables:
            tffo_cols = {
                c["name"]: c
                for c in inspector.get_columns("tenant_feature_flag_overrides")
            }
            print(f"\ntenant_feature_flag_overrides columns: {list(tffo_cols.keys())}")
            for column in ("reason", "set_by"):
                if column in tffo_cols:
                    print(f"  OK: '{column}' column present")
                else:
                    print(f"  MISSING: '{column}' column")
                    issues.append(
                        f"tenant_feature_flag_overrides missing '{column}' column"
                    )

    if issues:
        print(f"\nISSUES FOUND ({len(issues)}):", file=sys.stderr)
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        return 1

    print("\nNo issues found! All FK references validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
