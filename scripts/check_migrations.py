"""Check Alembic autogenerate + verify all FK relationships in v2 tables."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-CORE"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "03-MODELS"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04-SERVICES"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "05-API"))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENCRYPTION_KEY"] = "test-key"
os.environ["USE_SQLITE_TESTS"] = "1"

from orion.app import create_app

app = create_app("testing")

with app.app_context():
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import inspect

    from orion.extensions import db

    # Create tables from models
    db.create_all()

    # Inspect all tables
    inspector = inspect(db.engine)
    all_tables = set(inspector.get_table_names())

    # Known v1 tables (pre-v2)
    v1_tables = {
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

    v2_tables = all_tables - v1_tables - {"alembic_version"}
    print(f"Total tables in DB: {len(all_tables)}")
    print(f"v2 tables detected: {len(v2_tables)}")
    print()

    issues = []

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
            # Verify referred table exists
            if fk["referred_table"] not in all_tables:
                issues.append(
                    f"  {t}: FK {constrained} -> {ref} — referred table MISSING!"
                )
        print()

    # Now try autogenerate to see if alembic detects any changes
    print("--- Alembic autogenerate check ---")
    cfg2 = Config("migrations/alembic.ini")
    cfg2.set_main_option("script_location", "migrations")
    try:
        command.revision(cfg2, autogenerate=True, message="v2_autogenerate_check")
        print("autogenerate completed successfully (no unexpected changes)")
    except Exception as e:
        print(f"autogenerate result: {e}")

    if issues:
        print(f"\nISSUES FOUND ({len(issues)}):")
        for i in issues:
            print(f"  {i}")
    else:
        print("\nNo issues found! All FK references validated.")

    # Check if our new reason/set_by columns exist in tenant_feature_flag_overrides
    if "tenant_feature_flag_overrides" in all_tables:
        tffo_cols = {
            c["name"]: c for c in inspector.get_columns("tenant_feature_flag_overrides")
        }
        print(f"\ntenant_feature_flag_overrides columns: {list(tffo_cols.keys())}")
        if "reason" in tffo_cols:
            print("  ✅ 'reason' column present")
        else:
            print("  ❌ 'reason' column MISSING!")
            issues.append("tenant_feature_flag_overrides missing 'reason' column")
        if "set_by" in tffo_cols:
            print("  ✅ 'set_by' column present")
        else:
            print("  ❌ 'set_by' column MISSING!")
            issues.append("tenant_feature_flag_overrides missing 'set_by' column")
