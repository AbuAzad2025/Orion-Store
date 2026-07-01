-- ============================================================================
-- Wave 12 Hardening: PostgreSQL Row-Level Security (RLS) for v2 Tables
-- Generated from audit of migration v2_all_001
-- ============================================================================
-- This script adds RLS policies to all v2 tables that are tenant-scoped.
-- Tables already having RLS (in migration): subscription_plans, customer_subscriptions,
-- subscription_invoices, digital_assets, store_credits, draft_orders, tax_jurisdictions,
-- product_bundles, metafield_definitions, pickup_locations (10 tables).
-- 
-- Platform-wide tables (no RLS needed): platform_audit_reports, platform_admin_audit_log,
-- currency_rates (system-wide reference data)
--
-- Run this AFTER migration v2_all_001 is applied.
-- ============================================================================

-- Helper: Enable RLS and create tenant_isolation policy for a tenant-scoped table
-- Usage: \i this_file.sql  (in psql) or execute via alembic

DO $$
DECLARE
    tbl text;
BEGIN
    -- List of tenant-scoped v2 tables missing RLS
    FOR tbl IN SELECT unnest(ARRAY[
        -- Subscriptions module (3 missing)
        'subscription_events',
        'digital_downloads',
        'license_keys',
        
        -- Store Credit (1 missing)
        'store_credit_transactions',
        
        -- Draft Orders (1 missing)
        'draft_order_items',
        
        -- Tax (2 missing)
        'tax_rates',
        'tax_nexus_rules',
        
        -- Bundles (1 missing)
        'bundle_items',
        
        -- Metafields (1 missing)
        'metafields',
        
        -- BOPIS (1 missing)
        'pickup_slots',
        
        -- Inventory Transfers (2 missing)
        'inventory_transfers',
        'inventory_transfer_items',
        
        -- Import/Export (1 missing)
        'import_export_jobs',
        
        -- Stock Notifications (1 missing)
        'stock_notifications',
        
        -- App Platform (4 missing)
        'oauth_applications',
        'app_installations',
        'app_webhook_subscriptions',
        'sandbox_stores',
        
        -- Fraud (3 missing)
        'fraud_rules',
        'fraud_reviews',
        'chargebacks',
        
        -- Compliance (4 missing)
        'consent_records',
        'data_subject_requests',
        'cookie_consent_settings',
        'sso_providers',
        
        -- Workflow (2 missing)
        'workflow_definitions',
        'workflow_runs',
        
        -- Search Merchandising (3 missing)
        'search_synonyms',
        'search_redirects',
        'search_boost_rules',
        
        -- Affiliates (4 missing)
        'affiliate_programs',
        'affiliates',
        'affiliate_commissions',
        'affiliate_links',
        
        -- Gift Registries (2 missing)
        'gift_registries',
        'gift_registry_items',
        
        -- Dropship (3 missing)
        'pod_connections',
        'dropship_suppliers',
        'dropship_orders',
        
        -- Schema Markup (1 missing)
        'product_schema_markup',
        
        -- Accessibility (1 missing)
        'accessibility_audits',
        
        -- Live Chat (2 missing)
        'live_chat_sessions',
        'live_chat_messages',
        
        -- Financial Reconciliation v2 (2 missing)
        'financial_reconciliation_runs',
        'financial_reconciliation_items',
        
        -- Tenant Feature Flag Overrides (1 missing - created in this migration but no RLS)
        'tenant_feature_flag_overrides'
    ]) LOOP
        BEGIN
            EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
            EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', tbl);
            EXECUTE format('
                CREATE POLICY tenant_isolation ON %I
                USING (
                    tenant_id = NULLIF(current_setting(''app.tenant_id'', true), '''')::bigint
                )
            ', tbl);
            RAISE NOTICE 'RLS enabled + policy created for %', tbl;
        EXCEPTION WHEN undefined_table THEN
            RAISE NOTICE 'Table % does not exist, skipping', tbl;
        END;
    END LOOP;
END $$;

-- ============================================================================
-- Verification: List all tables with RLS enabled
-- ============================================================================
-- SELECT tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies 
-- WHERE schemaname = 'public' 
--   AND policyname = 'tenant_isolation'
-- ORDER BY tablename;