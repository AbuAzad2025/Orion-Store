"""Baseline schema — indexes (squashed).

Revision ID: baseline_0002
Revises: baseline_0001
Create Date: 2026-11-19
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "baseline_0002"
down_revision = "baseline_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE UNIQUE INDEX ix_revoked_tokens_jti ON revoked_tokens (jti)")
    op.execute(
        "CREATE INDEX ix_accessibility_audits_tenant_id ON accessibility_audits (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_affiliate_programs_tenant_id ON affiliate_programs (tenant_id)"
    )
    op.execute("CREATE INDEX ix_bnpl_providers_tenant_id ON bnpl_providers (tenant_id)")
    op.execute("CREATE INDEX ix_brands_tenant_id ON brands (tenant_id)")
    op.execute("CREATE INDEX ix_categories_tenant_id ON categories (tenant_id)")
    op.execute("CREATE INDEX ix_cms_pages_tenant_id ON cms_pages (tenant_id)")
    op.execute(
        "CREATE INDEX ix_consent_records_customer_email ON consent_records (customer_email)"
    )
    op.execute(
        "CREATE INDEX ix_consent_records_tenant_id ON consent_records (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_cookie_consent_settings_tenant_id ON cookie_consent_settings (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_data_subject_requests_tenant_id ON data_subject_requests (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_dropship_suppliers_tenant_id ON dropship_suppliers (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_financial_events_tenant_id ON financial_events (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_financial_reconciliation_runs_tenant_id ON financial_reconciliation_runs (tenant_id)"
    )
    op.execute("CREATE INDEX ix_fraud_rules_tenant_id ON fraud_rules (tenant_id)")
    op.execute(
        "CREATE INDEX ix_metafield_definitions_tenant_id ON metafield_definitions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_oauth_applications_tenant_id ON oauth_applications (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_pod_connections_tenant_id ON pod_connections (tenant_id)"
    )
    op.execute("CREATE INDEX ix_price_lists_tenant_id ON price_lists (tenant_id)")
    op.execute(
        "CREATE INDEX ix_product_bundles_tenant_id ON product_bundles (tenant_id)"
    )
    op.execute("CREATE INDEX ix_return_reasons_tenant_id ON return_reasons (tenant_id)")
    op.execute("CREATE INDEX ix_roles_tenant_id ON roles (tenant_id)")
    op.execute("CREATE INDEX ix_sandbox_stores_tenant_id ON sandbox_stores (tenant_id)")
    op.execute(
        "CREATE INDEX ix_search_redirects_tenant_id ON search_redirects (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_search_synonyms_tenant_id ON search_synonyms (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_shipping_methods_tenant_id ON shipping_methods (tenant_id)"
    )
    op.execute("CREATE INDEX ix_shipping_zones_tenant_id ON shipping_zones (tenant_id)")
    op.execute("CREATE INDEX ix_sso_providers_tenant_id ON sso_providers (tenant_id)")
    op.execute(
        "CREATE INDEX ix_subscription_plans_tenant_id ON subscription_plans (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_tax_jurisdictions_tenant_id ON tax_jurisdictions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_tenant_document_templates_tenant_id ON tenant_document_templates (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_tenant_payment_gateways_tenant_id ON tenant_payment_gateways (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_translation_glossary_tenant_id ON translation_glossary (tenant_id)"
    )
    op.execute("CREATE INDEX ix_users_tenant_id ON users (tenant_id)")
    op.execute("CREATE INDEX ix_vouchers_tenant_id ON vouchers (tenant_id)")
    op.execute("CREATE INDEX ix_warehouses_tenant_id ON warehouses (tenant_id)")
    op.execute(
        "CREATE INDEX ix_workflow_definitions_tenant_id ON workflow_definitions (tenant_id)"
    )
    op.execute("CREATE INDEX ix_affiliates_tenant_id ON affiliates (tenant_id)")
    op.execute(
        "CREATE INDEX ix_app_installations_tenant_id ON app_installations (tenant_id)"
    )
    op.execute("CREATE INDEX ix_audit_logs_tenant_id ON audit_logs (tenant_id)")
    op.execute("CREATE INDEX ix_carts_tenant_id ON carts (tenant_id)")
    op.execute(
        "CREATE INDEX ix_category_translations_tenant_id ON category_translations (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_customer_groups_tenant_id ON customer_groups (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_customer_subscriptions_plan_id ON customer_subscriptions (plan_id)"
    )
    op.execute(
        "CREATE INDEX ix_customer_subscriptions_tenant_id ON customer_subscriptions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_feature_flag_overrides_tenant_id ON feature_flag_overrides (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_financial_reconciliation_items_run_id ON financial_reconciliation_items (run_id)"
    )
    op.execute(
        "CREATE INDEX ix_financial_reconciliation_items_tenant_id ON financial_reconciliation_items (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_gift_registries_tenant_id ON gift_registries (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_impersonation_sessions_impersonator_user_id ON impersonation_sessions (impersonator_user_id)"
    )
    op.execute(
        "CREATE INDEX ix_impersonation_sessions_target_user_id ON impersonation_sessions (target_user_id)"
    )
    op.execute(
        "CREATE INDEX ix_impersonation_sessions_tenant_id ON impersonation_sessions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_import_export_jobs_tenant_id ON import_export_jobs (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_inventory_transfers_tenant_id ON inventory_transfers (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_live_chat_sessions_tenant_id ON live_chat_sessions (tenant_id)"
    )
    op.execute("CREATE INDEX ix_metafields_definition_id ON metafields (definition_id)")
    op.execute("CREATE INDEX ix_metafields_owner_id ON metafields (owner_id)")
    op.execute("CREATE INDEX ix_metafields_tenant_id ON metafields (tenant_id)")
    op.execute("CREATE INDEX ix_orders_tenant_id ON orders (tenant_id)")
    op.execute(
        "CREATE INDEX ix_page_translations_tenant_id ON page_translations (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_pickup_locations_tenant_id ON pickup_locations (tenant_id)"
    )
    op.execute("CREATE INDEX ix_products_tenant_id ON products (tenant_id)")
    op.execute(
        "CREATE INDEX ix_shipping_rates_shipping_method_id ON shipping_rates (shipping_method_id)"
    )
    op.execute(
        "CREATE INDEX ix_shipping_rates_shipping_zone_id ON shipping_rates (shipping_zone_id)"
    )
    op.execute("CREATE INDEX ix_shipping_rates_tenant_id ON shipping_rates (tenant_id)")
    op.execute(
        "CREATE INDEX ix_store_credits_customer_email ON store_credits (customer_email)"
    )
    op.execute("CREATE INDEX ix_store_credits_tenant_id ON store_credits (tenant_id)")
    op.execute(
        "CREATE INDEX ix_tax_nexus_rules_tenant_id ON tax_nexus_rules (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_tax_rates_jurisdiction_id ON tax_rates (jurisdiction_id)"
    )
    op.execute("CREATE INDEX ix_tax_rates_tenant_id ON tax_rates (tenant_id)")
    op.execute(
        "CREATE INDEX ix_tenant_feature_flag_overrides_tenant_id ON tenant_feature_flag_overrides (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_workflow_runs_definition_id ON workflow_runs (definition_id)"
    )
    op.execute("CREATE INDEX ix_workflow_runs_tenant_id ON workflow_runs (tenant_id)")
    op.execute(
        "CREATE INDEX ix_affiliate_commissions_affiliate_id ON affiliate_commissions (affiliate_id)"
    )
    op.execute(
        "CREATE INDEX ix_affiliate_commissions_tenant_id ON affiliate_commissions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_affiliate_links_affiliate_id ON affiliate_links (affiliate_id)"
    )
    op.execute(
        "CREATE INDEX ix_affiliate_links_tenant_id ON affiliate_links (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_app_webhook_subscriptions_tenant_id ON app_webhook_subscriptions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_bnpl_transactions_order_id ON bnpl_transactions (order_id)"
    )
    op.execute(
        "CREATE INDEX ix_bnpl_transactions_tenant_id ON bnpl_transactions (tenant_id)"
    )
    op.execute("CREATE INDEX ix_bundle_items_bundle_id ON bundle_items (bundle_id)")
    op.execute("CREATE INDEX ix_bundle_items_tenant_id ON bundle_items (tenant_id)")
    op.execute("CREATE INDEX ix_cart_items_tenant_id ON cart_items (tenant_id)")
    op.execute(
        "CREATE INDEX ix_customer_group_members_tenant_id ON customer_group_members (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_digital_assets_product_id ON digital_assets (product_id)"
    )
    op.execute("CREATE INDEX ix_digital_assets_tenant_id ON digital_assets (tenant_id)")
    op.execute("CREATE INDEX ix_draft_orders_tenant_id ON draft_orders (tenant_id)")
    op.execute("CREATE INDEX ix_dropship_orders_order_id ON dropship_orders (order_id)")
    op.execute(
        "CREATE INDEX ix_dropship_orders_supplier_id ON dropship_orders (supplier_id)"
    )
    op.execute(
        "CREATE INDEX ix_dropship_orders_tenant_id ON dropship_orders (tenant_id)"
    )
    op.execute("CREATE INDEX ix_fraud_reviews_order_id ON fraud_reviews (order_id)")
    op.execute("CREATE INDEX ix_fraud_reviews_tenant_id ON fraud_reviews (tenant_id)")
    op.execute("CREATE INDEX ix_fulfillments_order_id ON fulfillments (order_id)")
    op.execute("CREATE INDEX ix_fulfillments_tenant_id ON fulfillments (tenant_id)")
    op.execute(
        "CREATE INDEX ix_gift_registry_items_registry_id ON gift_registry_items (registry_id)"
    )
    op.execute(
        "CREATE INDEX ix_gift_registry_items_tenant_id ON gift_registry_items (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_inventory_levels_tenant_id ON inventory_levels (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_inventory_transfer_items_tenant_id ON inventory_transfer_items (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_inventory_transfer_items_transfer_id ON inventory_transfer_items (transfer_id)"
    )
    op.execute(
        "CREATE INDEX ix_live_chat_messages_session_id ON live_chat_messages (session_id)"
    )
    op.execute(
        "CREATE INDEX ix_live_chat_messages_tenant_id ON live_chat_messages (tenant_id)"
    )
    op.execute("CREATE INDEX ix_order_events_tenant_id ON order_events (tenant_id)")
    op.execute("CREATE INDEX ix_order_items_tenant_id ON order_items (tenant_id)")
    op.execute("CREATE INDEX ix_payments_tenant_id ON payments (tenant_id)")
    op.execute("CREATE INDEX ix_pickup_slots_location_id ON pickup_slots (location_id)")
    op.execute("CREATE INDEX ix_pickup_slots_tenant_id ON pickup_slots (tenant_id)")
    op.execute(
        "CREATE INDEX ix_price_list_items_price_list_id ON price_list_items (price_list_id)"
    )
    op.execute(
        "CREATE INDEX ix_price_list_items_tenant_id ON price_list_items (tenant_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_product_schema_markup_product_id ON product_schema_markup (product_id)"
    )
    op.execute(
        "CREATE INDEX ix_product_schema_markup_tenant_id ON product_schema_markup (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_product_translations_tenant_id ON product_translations (tenant_id)"
    )
    op.execute("CREATE INDEX ix_quotes_tenant_id ON quotes (tenant_id)")
    op.execute("CREATE INDEX ix_returns_order_id ON returns (order_id)")
    op.execute("CREATE INDEX ix_returns_tenant_id ON returns (tenant_id)")
    op.execute(
        "CREATE INDEX ix_search_boost_rules_tenant_id ON search_boost_rules (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_stock_notifications_product_id ON stock_notifications (product_id)"
    )
    op.execute(
        "CREATE INDEX ix_stock_notifications_tenant_id ON stock_notifications (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_store_credit_transactions_credit_id ON store_credit_transactions (credit_id)"
    )
    op.execute(
        "CREATE INDEX ix_store_credit_transactions_tenant_id ON store_credit_transactions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_subscription_events_subscription_id ON subscription_events (subscription_id)"
    )
    op.execute(
        "CREATE INDEX ix_subscription_events_tenant_id ON subscription_events (tenant_id)"
    )
    op.execute("CREATE INDEX ix_chargebacks_payment_id ON chargebacks (payment_id)")
    op.execute("CREATE INDEX ix_chargebacks_tenant_id ON chargebacks (tenant_id)")
    op.execute(
        "CREATE INDEX ix_digital_downloads_asset_id ON digital_downloads (asset_id)"
    )
    op.execute(
        "CREATE INDEX ix_digital_downloads_order_id ON digital_downloads (order_id)"
    )
    op.execute(
        "CREATE INDEX ix_digital_downloads_tenant_id ON digital_downloads (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_draft_order_items_draft_order_id ON draft_order_items (draft_order_id)"
    )
    op.execute(
        "CREATE INDEX ix_draft_order_items_tenant_id ON draft_order_items (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_fulfillment_items_fulfillment_id ON fulfillment_items (fulfillment_id)"
    )
    op.execute(
        "CREATE INDEX ix_fulfillment_items_tenant_id ON fulfillment_items (tenant_id)"
    )
    op.execute("CREATE INDEX ix_invoices_tenant_id ON invoices (tenant_id)")
    op.execute(
        "CREATE INDEX ix_license_keys_order_item_id ON license_keys (order_item_id)"
    )
    op.execute("CREATE INDEX ix_license_keys_tenant_id ON license_keys (tenant_id)")
    op.execute(
        "CREATE INDEX ix_platform_commission_ledger_reverses_ledger_id ON platform_commission_ledger (reverses_ledger_id)"
    )
    op.execute(
        "CREATE INDEX ix_platform_commission_ledger_tenant_id ON platform_commission_ledger (tenant_id)"
    )
    op.execute("CREATE INDEX ix_quote_items_quote_id ON quote_items (quote_id)")
    op.execute("CREATE INDEX ix_quote_items_tenant_id ON quote_items (tenant_id)")
    op.execute("CREATE INDEX ix_refunds_tenant_id ON refunds (tenant_id)")
    op.execute("CREATE INDEX ix_return_items_return_id ON return_items (return_id)")
    op.execute("CREATE INDEX ix_return_items_tenant_id ON return_items (tenant_id)")
    op.execute(
        "CREATE INDEX ix_subscription_invoices_subscription_id ON subscription_invoices (subscription_id)"
    )
    op.execute(
        "CREATE INDEX ix_subscription_invoices_tenant_id ON subscription_invoices (tenant_id)"
    )

    op.execute(
        "CREATE INDEX ix_categories_tenant_active ON categories USING btree (tenant_id, sort_order, name) WHERE (deleted_at IS NULL)"
    )
    op.execute(
        "CREATE INDEX ix_category_translations_tenant_locale ON category_translations USING btree (tenant_id, locale)"
    )
    op.execute(
        "CREATE INDEX ix_feature_flags_category ON feature_flags USING btree (category)"
    )
    op.execute(
        "CREATE INDEX ix_platform_admin_audit_log_user_id ON platform_admin_audit_log USING btree (user_id)"
    )
    op.execute(
        "CREATE INDEX ix_product_translations_tenant_locale ON product_translations USING btree (tenant_id, locale)"
    )
    op.execute(
        "CREATE INDEX ix_products_tenant_published_active ON products USING btree (tenant_id, created_at DESC) WHERE ((deleted_at IS NULL) AND (is_published = true))"
    )
    op.execute(
        "CREATE INDEX ix_tenant_gateways_tenant ON tenant_payment_gateways USING btree (tenant_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX product_schema_markup_product_id_key ON product_schema_markup USING btree (product_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_payments_order_active ON payments USING btree (order_id) WHERE (status IN ('pending', 'processing', 'completed', 'refunded'))"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    bind = op.get_bind()
    inspector = inspect(bind)
    for table in inspector.get_table_names():
        if table == "alembic_version":
            continue
        for index in inspector.get_indexes(table):
            name = index.get("name")
            if not name:
                continue
            # Constraint-backed unique indexes must be dropped via
            # the constraint; standalone indexes via DROP INDEX.
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
            op.execute(f"DROP INDEX IF EXISTS {name}")
