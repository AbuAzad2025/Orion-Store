"""Baseline schema — all tables (squashed).

Revision ID: baseline_0001
Revises: None
Create Date: 2026-11-19
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "baseline_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "CREATE TABLE currency_rates (\n\tid BIGSERIAL NOT NULL, \n\tfrom_currency VARCHAR(3) NOT NULL, \n\tto_currency VARCHAR(3) NOT NULL, \n\trate NUMERIC(12, 6) NOT NULL, \n\trate_date DATE DEFAULT CURRENT_DATE NOT NULL, \n\tsource VARCHAR(50) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_currency_rates UNIQUE (from_currency, to_currency, rate_date)\n)"
    )
    op.execute(
        "CREATE TABLE feature_flags (\n\tid BIGSERIAL NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcode VARCHAR(100) NOT NULL, \n\tdescription TEXT, \n\tcategory VARCHAR(50) NOT NULL, \n\tdefault_value BOOLEAN NOT NULL, \n\tscope VARCHAR(20) NOT NULL, \n\tis_system BOOLEAN NOT NULL, \n\trollout_percent INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)"
    )
    op.execute(
        "CREATE TABLE locales (\n\tid BIGSERIAL NOT NULL, \n\tcode VARCHAR(5) NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tdirection VARCHAR(3) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)"
    )
    op.execute(
        "CREATE TABLE permissions (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcode VARCHAR(100) NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\tdescription TEXT, \n\tcategory VARCHAR(50) NOT NULL, \n\tis_system BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)"
    )
    op.execute(
        "CREATE TABLE platform_settings (\n\tid SERIAL NOT NULL, \n\tplatform_name VARCHAR(100) NOT NULL, \n\tplatform_logo_url VARCHAR(500), \n\tplatform_logo_dark_url VARCHAR(500), \n\tfooter_html TEXT NOT NULL, \n\towner_name VARCHAR(200) NOT NULL, \n\towner_phone VARCHAR(50) NOT NULL, \n\towner_phone_intl VARCHAR(50) NOT NULL, \n\towner_email VARCHAR(255), \n\tsupport_email VARCHAR(255), \n\tdefault_currency VARCHAR(3) DEFAULT 'ILS' NOT NULL, \n\tdefault_language VARCHAR(5) DEFAULT 'ar' NOT NULL, \n\tdefault_commission_percent NUMERIC(5, 4) NOT NULL, \n\tsingleton VARCHAR(1) NOT NULL, \n\tvaluepayment_enabled BOOLEAN NOT NULL, \n\tvaluepayment_config JSON NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (singleton)\n)"
    )
    op.execute(
        "CREATE TABLE revoked_tokens (\n\tid BIGSERIAL NOT NULL, \n\tjti VARCHAR(36) NOT NULL, \n\ttoken_type VARCHAR(20) NOT NULL, \n\tuser_public_id VARCHAR(64), \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id)\n)"
    )
    op.execute(
        "CREATE TABLE tenants (\n\tid BIGSERIAL NOT NULL, \n\tpublic_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tversion INTEGER NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tname_en VARCHAR(100), \n\tlogo_url VARCHAR(500), \n\tslug VARCHAR(100) NOT NULL, \n\tdomain VARCHAR(255), \n\tcustom_domain VARCHAR(255), \n\temail VARCHAR(255) NOT NULL, \n\tphone VARCHAR(50), \n\tcountry_code VARCHAR(2) NOT NULL, \n\tdefault_language VARCHAR(5) NOT NULL, \n\tdefault_currency VARCHAR(3) NOT NULL, \n\ttimezone VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tplan_type VARCHAR(20) NOT NULL, \n\ttrial_ends_at TIMESTAMP WITH TIME ZONE, \n\tsuspended_until TIMESTAMP WITH TIME ZONE, \n\tsuspended_reason VARCHAR(500), \n\tplatform_commission_percent NUMERIC(5, 4), \n\tonboarding_completed BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (public_id), \n\tUNIQUE (slug), \n\tUNIQUE (domain), \n\tUNIQUE (custom_domain)\n)"
    )
    op.execute(
        "CREATE TABLE accessibility_audits (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tpage_url VARCHAR(1024) NOT NULL, \n\tscore INTEGER NOT NULL, \n\tissues JSON NOT NULL, \n\trecommendations TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE affiliate_programs (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\tcommission_type VARCHAR(20) NOT NULL, \n\tcommission_value NUMERIC(5, 2) NOT NULL, \n\tcookie_days INTEGER NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_aff_programs UNIQUE (tenant_id, code), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE bnpl_providers (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tprovider VARCHAR(20) NOT NULL, \n\tis_enabled BOOLEAN NOT NULL, \n\tmerchant_id VARCHAR(255), \n\tapi_credentials_encrypted TEXT, \n\tconfig JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_bnpl_providers_tenant UNIQUE (tenant_id, provider), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE brands (\n\tid BIGSERIAL NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tslug VARCHAR(255) NOT NULL, \n\tdescription TEXT, \n\tlogo_url VARCHAR(500), \n\twebsite_url VARCHAR(500), \n\ttenant_id BIGINT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_brands_slug UNIQUE (slug, tenant_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE categories (\n\tid BIGSERIAL NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tslug VARCHAR(255) NOT NULL, \n\tdescription TEXT, \n\tshort_description VARCHAR(500), \n\tparent_id BIGINT, \n\tlevel INTEGER NOT NULL, \n\tpath VARCHAR(500), \n\timage_url VARCHAR(500), \n\tsort_order INTEGER NOT NULL, \n\tis_featured BOOLEAN NOT NULL, \n\tis_visible BOOLEAN NOT NULL, \n\tshow_in_menu BOOLEAN NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_categories_slug UNIQUE (slug, tenant_id), \n\tFOREIGN KEY(parent_id) REFERENCES categories (id) ON DELETE SET NULL, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE cms_pages (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tslug VARCHAR(255) NOT NULL, \n\ttitle VARCHAR(255) NOT NULL, \n\tis_published BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_cms_pages_tenant_slug UNIQUE (tenant_id, slug), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE consent_records (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcustomer_email VARCHAR(255) NOT NULL, \n\tconsent_type VARCHAR(50) NOT NULL, \n\tgranted BOOLEAN NOT NULL, \n\tip_address VARCHAR(45), \n\tuser_agent TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE cookie_consent_settings (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tnecessary_cookies JSON NOT NULL, \n\tanalytics_cookies JSON NOT NULL, \n\tmarketing_cookies JSON NOT NULL, \n\tbanner_message TEXT, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE data_subject_requests (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcustomer_email VARCHAR(255) NOT NULL, \n\trequest_type VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE dropship_suppliers (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tcontact_email VARCHAR(255) NOT NULL, \n\tcontact_phone VARCHAR(50), \n\tfulfillment_time_days INTEGER NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE financial_events (\n\tid BIGSERIAL NOT NULL, \n\tpublic_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tdirection VARCHAR(10) NOT NULL, \n\tevent_type VARCHAR(50) NOT NULL, \n\tamount NUMERIC(12, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tsource_entity VARCHAR(30) NOT NULL, \n\tsource_id BIGINT NOT NULL, \n\tgateway_id BIGINT, \n\tplatform_gateway_id BIGINT, \n\texternal_reference VARCHAR(255), \n\tdescription TEXT, \n\tmetadata JSON NOT NULL, \n\tcommission_applied BOOLEAN NOT NULL, \n\tcommission_percent NUMERIC(5, 4), \n\tcommission_amount NUMERIC(10, 2), \n\tcommission_ledger_id BIGINT, \n\tstatus VARCHAR(20) NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tUNIQUE (public_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE financial_reconciliation_runs (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\trun_number VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\ttotal_events INTEGER NOT NULL, \n\tmatched_count INTEGER NOT NULL, \n\tdiscrepancy_count INTEGER NOT NULL, \n\tcompleted_at VARCHAR(50), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (run_number)\n)"
    )
    op.execute(
        "CREATE TABLE fraud_rules (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\trule_type VARCHAR(50) NOT NULL, \n\toperator VARCHAR(20) NOT NULL, \n\tthreshold_value NUMERIC(10, 2) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\taction VARCHAR(20) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE metafield_definitions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\towner_type VARCHAR(50) NOT NULL, \n\tkey VARCHAR(100) NOT NULL, \n\tlabel VARCHAR(255) NOT NULL, \n\tfield_type VARCHAR(50) NOT NULL, \n\tis_required BOOLEAN NOT NULL, \n\tdefault_value TEXT, \n\tvalidation_rules JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_metafield_def UNIQUE (tenant_id, owner_type, key), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE oauth_applications (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tredirect_uris JSON NOT NULL, \n\tclient_id VARCHAR(255) NOT NULL, \n\tclient_secret_hash VARCHAR(255) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tscopes JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (client_id)\n)"
    )
    op.execute(
        "CREATE TABLE pod_connections (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tprovider VARCHAR(50) NOT NULL, \n\tapi_key_hash VARCHAR(255) NOT NULL, \n\tapi_url VARCHAR(1024), \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE price_lists (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tis_default BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE product_bundles (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tname_en VARCHAR(255), \n\timage_url VARCHAR(500), \n\tslug VARCHAR(255) NOT NULL, \n\tdescription TEXT, \n\tbundle_price NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tis_published BOOLEAN NOT NULL, \n\tmax_per_order INTEGER, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE return_reasons (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\tlabel VARCHAR(255) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tsort_order INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_return_reasons_code UNIQUE (tenant_id, code), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE roles (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\tdescription TEXT, \n\tis_system_role BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE sandbox_stores (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tslug VARCHAR(100) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\texpires_at VARCHAR(50) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (slug)\n)"
    )
    op.execute(
        "CREATE TABLE search_redirects (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tquery_term VARCHAR(255) NOT NULL, \n\tredirect_url VARCHAR(1024) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE search_synonyms (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tterm VARCHAR(255) NOT NULL, \n\tsynonyms JSON NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE shipping_methods (\n\tid BIGSERIAL NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\tdescription TEXT, \n\tprovider VARCHAR(50), \n\ttype VARCHAR(20) NOT NULL, \n\tbase_cost NUMERIC(10, 2) NOT NULL, \n\tfree_shipping_threshold NUMERIC(10, 2), \n\tmin_order_value NUMERIC(10, 2), \n\tmax_order_value NUMERIC(10, 2), \n\testimated_days_min INTEGER, \n\testimated_days_max INTEGER, \n\tis_default BOOLEAN NOT NULL, \n\tsort_order INTEGER NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_shipping_methods_code_tenant UNIQUE (code, tenant_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE shipping_zones (\n\tid BIGSERIAL NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcountries JSON, \n\tregions JSON, \n\tpostal_codes JSON, \n\tis_default BOOLEAN NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE sso_providers (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tprovider_type VARCHAR(50) NOT NULL, \n\tclient_id VARCHAR(255) NOT NULL, \n\tclient_secret_hash VARCHAR(255) NOT NULL, \n\tissuer_url VARCHAR(1024), \n\tis_active BOOLEAN NOT NULL, \n\tauto_provision BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE subscription_plans (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tcode VARCHAR(100) NOT NULL, \n\tdescription TEXT, \n\tbilling_period_days INTEGER NOT NULL, \n\ttrial_period_days INTEGER NOT NULL, \n\tprice NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tmax_orders_per_cycle INTEGER, \n\tmax_products INTEGER, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_sub_plans_code UNIQUE (tenant_id, code), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE tax_jurisdictions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tcountry_code VARCHAR(2) NOT NULL, \n\tregion VARCHAR(100), \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_tax_jurisdictions UNIQUE (tenant_id, code), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE tenant_configs (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tbusiness_name VARCHAR(255), \n\ttax_rate NUMERIC(5, 4) NOT NULL, \n\ttax_included BOOLEAN NOT NULL, \n\tallow_guest_checkout BOOLEAN NOT NULL, \n\tcustom_css TEXT, \n\twebhook_url VARCHAR(500), \n\tPRIMARY KEY (id), \n\tUNIQUE (tenant_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE tenant_document_templates (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tdocument_type VARCHAR(30) NOT NULL, \n\tlocale VARCHAR(5) NOT NULL, \n\tbody_html TEXT, \n\tis_active BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE tenant_payment_gateways (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tprovider VARCHAR(30) NOT NULL, \n\tdisplay_name VARCHAR(100) NOT NULL, \n\tcredentials_encrypted TEXT, \n\twebhook_secret VARCHAR(255), \n\tis_enabled BOOLEAN NOT NULL, \n\tis_sandbox BOOLEAN NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tconfig JSON NOT NULL, \n\tconnected_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_tenant_gateway UNIQUE (tenant_id, provider), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE translation_glossary (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT, \n\tsource_locale VARCHAR(5) NOT NULL, \n\ttarget_locale VARCHAR(5) NOT NULL, \n\tsource_term VARCHAR(255) NOT NULL, \n\ttarget_term VARCHAR(255) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE users (\n\tid BIGSERIAL NOT NULL, \n\tpublic_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tversion INTEGER NOT NULL, \n\ttenant_id BIGINT, \n\temail VARCHAR(255) NOT NULL, \n\tpassword_hash VARCHAR(255) NOT NULL, \n\tfirst_name VARCHAR(100), \n\tlast_name VARCHAR(100), \n\tis_verified BOOLEAN NOT NULL, \n\tis_admin BOOLEAN NOT NULL, \n\tis_staff BOOLEAN NOT NULL, \n\tis_superuser BOOLEAN NOT NULL, \n\tis_customer BOOLEAN NOT NULL, \n\tlast_login_at TIMESTAMP WITH TIME ZONE, \n\tlanguage VARCHAR(5) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_users_superuser_no_tenant CHECK (NOT is_superuser OR tenant_id IS NULL), \n\tCONSTRAINT ck_users_tenant_customer CHECK (NOT is_superuser OR NOT is_customer), \n\tCONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email), \n\tUNIQUE (public_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE vouchers (\n\tid BIGSERIAL NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tdescription TEXT, \n\ttype VARCHAR(20) NOT NULL, \n\tvalue NUMERIC(10, 2) NOT NULL, \n\tmin_order_value NUMERIC(10, 2), \n\tmax_discount_amount NUMERIC(10, 2), \n\tusage_limit INTEGER, \n\tusage_count INTEGER NOT NULL, \n\tstart_date TIMESTAMP WITH TIME ZONE, \n\tend_date TIMESTAMP WITH TIME ZONE, \n\tis_free_shipping BOOLEAN NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_vouchers_code_tenant UNIQUE (code, tenant_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE warehouses (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\taddress JSON, \n\tis_active BOOLEAN NOT NULL, \n\tis_pickup_location BOOLEAN NOT NULL, \n\tpriority INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_warehouses_code UNIQUE (tenant_id, code), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE workflow_definitions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\ttrigger_event VARCHAR(100) NOT NULL, \n\tconditions JSON, \n\tactions JSON NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE affiliates (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tprogram_id BIGINT NOT NULL, \n\tuser_id BIGINT, \n\temail VARCHAR(255) NOT NULL, \n\treferral_code VARCHAR(50) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\ttotal_earned NUMERIC(10, 2) NOT NULL, \n\ttotal_paid NUMERIC(10, 2) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(program_id) REFERENCES affiliate_programs (id) ON DELETE CASCADE, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, \n\tUNIQUE (referral_code)\n)"
    )
    op.execute(
        "CREATE TABLE app_installations (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tapp_id BIGINT NOT NULL, \n\tinstalled_by BIGINT NOT NULL, \n\taccess_token_hash VARCHAR(255), \n\trefresh_token_hash VARCHAR(255), \n\tis_active BOOLEAN NOT NULL, \n\tsettings JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(app_id) REFERENCES oauth_applications (id) ON DELETE CASCADE, \n\tFOREIGN KEY(installed_by) REFERENCES users (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE audit_logs (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT, \n\tactor_user_id BIGINT, \n\taction VARCHAR(80) NOT NULL, \n\tresource_type VARCHAR(80) NOT NULL, \n\tresource_id VARCHAR(64), \n\tdetails JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE SET NULL, \n\tFOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE carts (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcart_token VARCHAR(255) NOT NULL, \n\tuser_id BIGINT, \n\tsession_id VARCHAR(255), \n\tstatus VARCHAR(20) NOT NULL, \n\tconverted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (cart_token), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE category_translations (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcategory_id BIGINT NOT NULL, \n\tlocale VARCHAR(5) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tdescription TEXT, \n\tslug VARCHAR(255), \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_category_trans_locale UNIQUE (category_id, locale), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE customer_groups (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcode VARCHAR(50) NOT NULL, \n\tdescription TEXT, \n\tdiscount_percent NUMERIC(5, 2) NOT NULL, \n\tprice_list_id BIGINT, \n\tmin_order_amount NUMERIC(10, 2), \n\tpayment_terms_days INTEGER NOT NULL, \n\tis_wholesale BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_customer_groups_code UNIQUE (tenant_id, code), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(price_list_id) REFERENCES price_lists (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE customer_subscriptions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tplan_id BIGINT NOT NULL, \n\tuser_id BIGINT, \n\tcustomer_email VARCHAR(255) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tcurrent_period_start TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcurrent_period_end TIMESTAMP WITH TIME ZONE NOT NULL, \n\ttrial_end TIMESTAMP WITH TIME ZONE, \n\tcancelled_at TIMESTAMP WITH TIME ZONE, \n\tpause_resume_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_cust_sub_email UNIQUE (tenant_id, customer_email), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(plan_id) REFERENCES subscription_plans (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE feature_flag_overrides (\n\tid BIGSERIAL NOT NULL, \n\tfeature_flag_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tvalue BOOLEAN NOT NULL, \n\treason TEXT, \n\tset_by BIGINT, \n\texpires_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_feature_flag_override_tenant UNIQUE (feature_flag_id, tenant_id), \n\tFOREIGN KEY(feature_flag_id) REFERENCES feature_flags (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(set_by) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE financial_reconciliation_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\trun_id BIGINT NOT NULL, \n\tfinancial_event_id BIGINT NOT NULL, \n\texpected_amount NUMERIC(10, 2) NOT NULL, \n\tactual_amount NUMERIC(10, 2) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tnotes TEXT, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(run_id) REFERENCES financial_reconciliation_runs (id) ON DELETE CASCADE, \n\tFOREIGN KEY(financial_event_id) REFERENCES financial_events (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE gift_registries (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tuser_id BIGINT, \n\tcustomer_email VARCHAR(255) NOT NULL, \n\tregistry_name VARCHAR(255) NOT NULL, \n\tevent_type VARCHAR(50), \n\tevent_date VARCHAR(50), \n\tdescription TEXT, \n\tis_public BOOLEAN NOT NULL, \n\tslug VARCHAR(255) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, \n\tUNIQUE (slug)\n)"
    )
    op.execute(
        "CREATE TABLE impersonation_sessions (\n\tid BIGSERIAL NOT NULL, \n\timpersonator_user_id BIGINT NOT NULL, \n\ttarget_user_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tended_at TIMESTAMP WITH TIME ZONE, \n\trevoked BOOLEAN NOT NULL, \n\tuser_agent VARCHAR(500), \n\tip_address VARCHAR(45), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(impersonator_user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(target_user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE import_export_jobs (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tjob_type VARCHAR(20) NOT NULL, \n\tentity_type VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(32) NOT NULL, \n\tfile_url VARCHAR(1024), \n\terror_log TEXT, \n\tprocessed_count INTEGER NOT NULL, \n\tfailed_count INTEGER NOT NULL, \n\ttotal_count INTEGER NOT NULL, \n\tuser_id BIGINT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE inventory_transfers (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\ttransfer_number VARCHAR(50) NOT NULL, \n\tfrom_warehouse_id BIGINT NOT NULL, \n\tto_warehouse_id BIGINT NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tnotes TEXT, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (transfer_number), \n\tFOREIGN KEY(from_warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(to_warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE live_chat_sessions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcustomer_email VARCHAR(255), \n\tsession_token VARCHAR(255) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tassigned_to BIGINT, \n\tended_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (session_token), \n\tFOREIGN KEY(assigned_to) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE metafields (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tdefinition_id BIGINT NOT NULL, \n\towner_id BIGINT NOT NULL, \n\tvalue TEXT, \n\tjson_value JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_metafield_value UNIQUE (definition_id, owner_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(definition_id) REFERENCES metafield_definitions (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE orders (\n\tid BIGSERIAL NOT NULL, \n\tpublic_id UUID NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tuser_id BIGINT, \n\torder_number VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tpayment_status VARCHAR(20) NOT NULL, \n\tfulfillment_status VARCHAR(20) NOT NULL, \n\tcustomer_email VARCHAR(255) NOT NULL, \n\tcustomer_first_name VARCHAR(100), \n\tcustomer_last_name VARCHAR(100), \n\tis_guest BOOLEAN NOT NULL, \n\tshipping_address JSON NOT NULL, \n\tshipping_method_code VARCHAR(50), \n\tsubtotal NUMERIC(10, 2) NOT NULL, \n\ttax_amount NUMERIC(10, 2) NOT NULL, \n\tshipping_cost NUMERIC(10, 2) NOT NULL, \n\tdiscount_amount NUMERIC(10, 2) NOT NULL, \n\tdiscount_code VARCHAR(100), \n\ttotal NUMERIC(10, 2) NOT NULL, \n\tidempotency_key VARCHAR(64), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tversion INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_orders_tenant_idempotency UNIQUE (tenant_id, idempotency_key), \n\tUNIQUE (public_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, \n\tUNIQUE (order_number)\n)"
    )
    op.execute(
        "CREATE TABLE page_translations (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tpage_id BIGINT NOT NULL, \n\tlocale VARCHAR(5) NOT NULL, \n\ttitle VARCHAR(255) NOT NULL, \n\tbody TEXT, \n\tslug VARCHAR(255), \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_page_trans_locale UNIQUE (page_id, locale), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(page_id) REFERENCES cms_pages (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE pickup_locations (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\twarehouse_id BIGINT, \n\tcode VARCHAR(50) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\taddress JSON NOT NULL, \n\tphone VARCHAR(50), \n\temail VARCHAR(255), \n\tis_active BOOLEAN NOT NULL, \n\tinstructions TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_pickup_locations UNIQUE (tenant_id, code), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE platform_admin_audit_log (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tuser_id BIGINT NOT NULL, \n\taction VARCHAR(100) NOT NULL, \n\ttarget_type VARCHAR(50), \n\ttarget_id INTEGER, \n\tdetails JSON, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE platform_audit_reports (\n\tid BIGSERIAL NOT NULL, \n\treport_number VARCHAR(50) NOT NULL, \n\treport_type VARCHAR(50) NOT NULL, \n\tgenerated_by BIGINT NOT NULL, \n\tsummary JSON NOT NULL, \n\tdetails JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (report_number), \n\tFOREIGN KEY(generated_by) REFERENCES users (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE products (\n\tid BIGSERIAL NOT NULL, \n\tpublic_id UUID NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tslug VARCHAR(255) NOT NULL, \n\tsku VARCHAR(100), \n\tdescription TEXT, \n\tshort_description VARCHAR(500), \n\timage_url VARCHAR(500), \n\tprice NUMERIC(10, 2) NOT NULL, \n\tcost_price NUMERIC(10, 2) NOT NULL DEFAULT 0, \n\tcompare_at_price NUMERIC(10, 2), \n\tquantity INTEGER NOT NULL, \n\tis_published BOOLEAN NOT NULL, \n\tis_featured BOOLEAN NOT NULL, \n\tcategory_id BIGINT, \n\tbrand_id BIGINT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tversion INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_products_slug UNIQUE (slug, tenant_id), \n\tCONSTRAINT ck_products_price_nonneg CHECK (price >= 0), \n\tCONSTRAINT ck_products_qty_nonneg CHECK (quantity >= 0), \n\tUNIQUE (public_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL, \n\tFOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE role_permissions (\n\trole_id BIGINT NOT NULL, \n\tpermission_id BIGINT NOT NULL, \n\tPRIMARY KEY (role_id, permission_id), \n\tFOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, \n\tFOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE shipping_rates (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tshipping_method_id BIGINT NOT NULL, \n\tshipping_zone_id BIGINT NOT NULL, \n\tprice NUMERIC(10, 2) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(shipping_method_id) REFERENCES shipping_methods (id) ON DELETE CASCADE, \n\tFOREIGN KEY(shipping_zone_id) REFERENCES shipping_zones (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE store_credits (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tcustomer_email VARCHAR(255) NOT NULL, \n\tuser_id BIGINT, \n\tbalance NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_store_credit_email UNIQUE (tenant_id, customer_email), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE tax_nexus_rules (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tjurisdiction_id BIGINT NOT NULL, \n\tnexus_type VARCHAR(20) NOT NULL, \n\tthreshold_amount NUMERIC(12, 2), \n\tthreshold_transactions INTEGER, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(jurisdiction_id) REFERENCES tax_jurisdictions (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE tax_rates (\n\tid BIGSERIAL NOT NULL, \n\tjurisdiction_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\trate NUMERIC(5, 4) NOT NULL, \n\tproduct_tax_code VARCHAR(50), \n\tis_compound BOOLEAN NOT NULL, \n\tpriority INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_tax_rates UNIQUE (jurisdiction_id, product_tax_code), \n\tFOREIGN KEY(jurisdiction_id) REFERENCES tax_jurisdictions (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE tenant_feature_flag_overrides (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tflag_id BIGINT NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\treason TEXT, \n\tset_by BIGINT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_tenant_feature_flag_override_tenant UNIQUE (tenant_id, flag_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(flag_id) REFERENCES feature_flags (id) ON DELETE CASCADE, \n\tFOREIGN KEY(set_by) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE user_roles (\n\tuser_id BIGINT NOT NULL, \n\trole_id BIGINT NOT NULL, \n\tassigned_by BIGINT, \n\tPRIMARY KEY (user_id, role_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, \n\tFOREIGN KEY(assigned_by) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE workflow_runs (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tdefinition_id BIGINT NOT NULL, \n\ttrigger_event_id INTEGER NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\terror_message TEXT, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(definition_id) REFERENCES workflow_definitions (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE affiliate_commissions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\taffiliate_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tamount NUMERIC(10, 2) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tpaid_at VARCHAR(50), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(affiliate_id) REFERENCES affiliates (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE affiliate_links (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\taffiliate_id BIGINT NOT NULL, \n\tproduct_id BIGINT, \n\turl VARCHAR(1024) NOT NULL, \n\tclick_count INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(affiliate_id) REFERENCES affiliates (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE app_webhook_subscriptions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tinstallation_id BIGINT NOT NULL, \n\ttopic VARCHAR(100) NOT NULL, \n\tcallback_url VARCHAR(1024) NOT NULL, \n\twebhook_secret VARCHAR(255), \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(installation_id) REFERENCES app_installations (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE bnpl_transactions (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tprovider VARCHAR(20) NOT NULL, \n\texternal_transaction_id VARCHAR(255) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tamount NUMERIC(10, 2) NOT NULL, \n\tinstallment_plan JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_bnpl_transactions_external UNIQUE (external_transaction_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE bundle_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\tbundle_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tdiscount_percent NUMERIC(5, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(bundle_id) REFERENCES product_bundles (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE cart_items (\n\tid BIGSERIAL NOT NULL, \n\tcart_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tunit_price NUMERIC(10, 2) NOT NULL, \n\ttotal_price NUMERIC(10, 2) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(cart_id) REFERENCES carts (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE customer_group_members (\n\tcustomer_group_id BIGINT NOT NULL, \n\tuser_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tPRIMARY KEY (customer_group_id, user_id), \n\tFOREIGN KEY(customer_group_id) REFERENCES customer_groups (id) ON DELETE CASCADE, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE digital_assets (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tfile_url VARCHAR(1024) NOT NULL, \n\tfile_name VARCHAR(255) NOT NULL, \n\tfile_size_bytes INTEGER, \n\tmime_type VARCHAR(100) NOT NULL, \n\tmax_downloads INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE draft_orders (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tdraft_number VARCHAR(50) NOT NULL, \n\tuser_id BIGINT, \n\tcustomer_email VARCHAR(255), \n\tcustomer_first_name VARCHAR(100), \n\tcustomer_last_name VARCHAR(100), \n\tstatus VARCHAR(20) NOT NULL, \n\tshipping_address JSON NOT NULL, \n\tnotes TEXT, \n\tsubtotal NUMERIC(10, 2) NOT NULL, \n\ttax_amount NUMERIC(10, 2) NOT NULL, \n\tshipping_cost NUMERIC(10, 2) NOT NULL, \n\tdiscount_amount NUMERIC(10, 2) NOT NULL, \n\ttotal NUMERIC(10, 2) NOT NULL, \n\tsend_email_invite BOOLEAN NOT NULL, \n\tconverted_order_id BIGINT, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (draft_number), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, \n\tFOREIGN KEY(converted_order_id) REFERENCES orders (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE dropship_orders (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tsupplier_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tsupplier_order_ref VARCHAR(255), \n\tstatus VARCHAR(20) NOT NULL, \n\tcost NUMERIC(10, 2) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(supplier_id) REFERENCES dropship_suppliers (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE fraud_reviews (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\trisk_score INTEGER NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\treviewed_by BIGINT, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, \n\tFOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE fulfillments (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\twarehouse_id BIGINT NOT NULL, \n\tfulfillment_number VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\ttracking_number VARCHAR(100), \n\tshipped_at TIMESTAMP WITH TIME ZONE, \n\tdelivered_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, \n\tFOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE gift_registry_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\tregistry_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\trequested_quantity INTEGER NOT NULL, \n\tpurchased_quantity INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(registry_id) REFERENCES gift_registries (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE inventory_levels (\n\tid BIGSERIAL NOT NULL, \n\twarehouse_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tquantity INTEGER NOT NULL, \n\treserved_quantity INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_inventory_levels_wh_product UNIQUE (warehouse_id, product_id), \n\tFOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE inventory_transfer_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\ttransfer_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(transfer_id) REFERENCES inventory_transfers (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE live_chat_messages (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tsession_id BIGINT NOT NULL, \n\tsender_type VARCHAR(20) NOT NULL, \n\tmessage TEXT NOT NULL, \n\tis_read BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(session_id) REFERENCES live_chat_sessions (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE order_events (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\torder_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tevent_type VARCHAR(50) NOT NULL, \n\tmessage TEXT, \n\tmetadata JSON, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE order_items (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\torder_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT, \n\tproduct_name VARCHAR(255) NOT NULL, \n\tproduct_sku VARCHAR(100), \n\tunit_price NUMERIC(10, 2) NOT NULL, \n\tunit_cost NUMERIC(10, 2) NOT NULL DEFAULT 0, \n\tquantity INTEGER NOT NULL, \n\ttotal_price NUMERIC(10, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE payments (\n\tid BIGSERIAL NOT NULL, \n\tpublic_id UUID NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tfinancial_event_id BIGINT, \n\tamount NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tpayment_method VARCHAR(50) NOT NULL, \n\tpayment_provider VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tprovider_payment_id VARCHAR(255), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (public_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(financial_event_id) REFERENCES financial_events (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE pickup_slots (\n\tid BIGSERIAL NOT NULL, \n\tlocation_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tday_of_week INTEGER NOT NULL, \n\tstart_time VARCHAR(5) NOT NULL, \n\tend_time VARCHAR(5) NOT NULL, \n\tmax_orders INTEGER NOT NULL, \n\tcurrent_orders INTEGER NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(location_id) REFERENCES pickup_locations (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE price_list_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\tprice_list_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tprice NUMERIC(10, 2) NOT NULL, \n\tmin_quantity INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_price_list_items UNIQUE (price_list_id, product_id, min_quantity), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(price_list_id) REFERENCES price_lists (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE product_schema_markup (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tschema_type VARCHAR(50) NOT NULL, \n\tjson_ld JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE product_translations (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tlocale VARCHAR(5) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tslug VARCHAR(255), \n\tdescription TEXT, \n\tmeta_title VARCHAR(255), \n\tmeta_description TEXT, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_product_trans_locale UNIQUE (product_id, locale), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE quotes (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tquote_number VARCHAR(50) NOT NULL, \n\tuser_id BIGINT, \n\tcustomer_group_id BIGINT, \n\tstatus VARCHAR(20) NOT NULL, \n\tsubtotal NUMERIC(12, 2) NOT NULL, \n\ttax_amount NUMERIC(10, 2) NOT NULL, \n\ttotal_amount NUMERIC(12, 2) NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE, \n\tconverted_order_id BIGINT, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (quote_number), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, \n\tFOREIGN KEY(customer_group_id) REFERENCES customer_groups (id) ON DELETE SET NULL, \n\tFOREIGN KEY(converted_order_id) REFERENCES orders (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE returns (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\treturn_number VARCHAR(50) NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tuser_id BIGINT, \n\tstatus VARCHAR(20) NOT NULL, \n\treturn_type VARCHAR(20) NOT NULL, \n\treason_id BIGINT, \n\treason_note TEXT, \n\trefund_amount NUMERIC(10, 2) NOT NULL, \n\trefund_method VARCHAR(20) NOT NULL, \n\tapproved_by BIGINT, \n\treceived_at TIMESTAMP WITH TIME ZONE, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (return_number), \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, \n\tFOREIGN KEY(reason_id) REFERENCES return_reasons (id) ON DELETE SET NULL, \n\tFOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE search_boost_rules (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT, \n\tcategory_id BIGINT, \n\tboost_factor INTEGER NOT NULL, \n\tquery_keyword VARCHAR(255), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE, \n\tFOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE stock_notifications (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tcustomer_email VARCHAR(255) NOT NULL, \n\tis_notified BOOLEAN NOT NULL, \n\tnotified_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE store_credit_transactions (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcredit_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\ttransaction_type VARCHAR(20) NOT NULL, \n\tamount NUMERIC(10, 2) NOT NULL, \n\tbalance_after NUMERIC(10, 2) NOT NULL, \n\treference_type VARCHAR(50), \n\treference_id INTEGER, \n\treason TEXT, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(credit_id) REFERENCES store_credits (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE subscription_events (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tsubscription_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tevent_type VARCHAR(50) NOT NULL, \n\tmessage TEXT, \n\tmetadata JSON, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(subscription_id) REFERENCES customer_subscriptions (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE chargebacks (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tpayment_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tamount NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\treason_code VARCHAR(50), \n\tstatus VARCHAR(20) NOT NULL, \n\tresponse_due_date VARCHAR(50), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE digital_downloads (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tasset_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tdownload_token VARCHAR(255) NOT NULL, \n\tdownload_count INTEGER NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(asset_id) REFERENCES digital_assets (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, \n\tUNIQUE (download_token)\n)"
    )
    op.execute(
        "CREATE TABLE draft_order_items (\n\tid BIGSERIAL NOT NULL, \n\tdraft_order_id BIGINT NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tproduct_id BIGINT, \n\tproduct_name VARCHAR(255) NOT NULL, \n\tproduct_sku VARCHAR(100), \n\tunit_price NUMERIC(10, 2) NOT NULL, \n\tquantity INTEGER NOT NULL, \n\ttotal_price NUMERIC(10, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(draft_order_id) REFERENCES draft_orders (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE fulfillment_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\tfulfillment_id BIGINT NOT NULL, \n\torder_item_id BIGINT NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(fulfillment_id) REFERENCES fulfillments (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE invoices (\n\tid BIGSERIAL NOT NULL, \n\tpublic_id UUID NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\torder_id BIGINT NOT NULL, \n\tfinancial_event_id BIGINT, \n\tpayment_id BIGINT, \n\tinvoice_number VARCHAR(50) NOT NULL, \n\tsubtotal NUMERIC(12, 2) NOT NULL, \n\ttax_amount NUMERIC(10, 2) NOT NULL, \n\ttotal_amount NUMERIC(12, 2) NOT NULL, \n\tcommission_amount NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tplatform_footer_applied BOOLEAN NOT NULL, \n\trendered_html TEXT, \n\tpdf_artifact_path VARCHAR(500), \n\tstorage_key VARCHAR(500), \n\tdocument_template_id BIGINT, \n\tissued_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (public_id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(financial_event_id) REFERENCES financial_events (id) ON DELETE SET NULL, \n\tFOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE SET NULL, \n\tUNIQUE (invoice_number), \n\tFOREIGN KEY(document_template_id) REFERENCES tenant_document_templates (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE license_keys (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\torder_item_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tkey VARCHAR(255) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tactivated_at TIMESTAMP WITH TIME ZONE, \n\texpires_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE, \n\tUNIQUE (key)\n)"
    )
    op.execute(
        "CREATE TABLE platform_commission_ledger (\n\tid BIGSERIAL NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tfinancial_event_id BIGINT NOT NULL, \n\treverses_ledger_id BIGINT, \n\tdirection VARCHAR(10) NOT NULL, \n\tentry_type VARCHAR(30) NOT NULL, \n\tpayment_id BIGINT, \n\torder_id BIGINT, \n\tgross_amount NUMERIC(12, 2) NOT NULL, \n\tcommission_percent NUMERIC(5, 4) NOT NULL, \n\tcommission_amount NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tnotes TEXT, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tUNIQUE (financial_event_id), \n\tFOREIGN KEY(financial_event_id) REFERENCES financial_events (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(reverses_ledger_id) REFERENCES platform_commission_ledger (id) ON DELETE SET NULL, \n\tFOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE SET NULL, \n\tFOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE quote_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\tquote_id BIGINT NOT NULL, \n\tproduct_id BIGINT NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tunit_price NUMERIC(10, 2) NOT NULL, \n\tdiscount_percent NUMERIC(5, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(quote_id) REFERENCES quotes (id) ON DELETE CASCADE, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE\n)"
    )
    op.execute(
        "CREATE TABLE refunds (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tpayment_id BIGINT NOT NULL, \n\tfinancial_event_id BIGINT, \n\tamount NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\treason VARCHAR(500), \n\tprovider_refund_id VARCHAR(255), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE CASCADE, \n\tFOREIGN KEY(financial_event_id) REFERENCES financial_events (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE return_items (\n\ttenant_id BIGINT NOT NULL, \n\tid BIGSERIAL NOT NULL, \n\treturn_id BIGINT NOT NULL, \n\torder_item_id BIGINT NOT NULL, \n\tproduct_id BIGINT, \n\tquantity INTEGER NOT NULL, \n\tcondition VARCHAR(20) NOT NULL, \n\trestock BOOLEAN NOT NULL, \n\trefund_amount NUMERIC(10, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(return_id) REFERENCES returns (id) ON DELETE CASCADE, \n\tFOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(product_id) REFERENCES products (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE subscription_invoices (\n\tid BIGSERIAL NOT NULL, \n\ttenant_id BIGINT NOT NULL, \n\tsubscription_id BIGINT NOT NULL, \n\tinvoice_number VARCHAR(50) NOT NULL, \n\tamount NUMERIC(10, 2) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tdue_date TIMESTAMP WITH TIME ZONE NOT NULL, \n\tpaid_at TIMESTAMP WITH TIME ZONE, \n\tpayment_id BIGINT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, \n\tFOREIGN KEY(subscription_id) REFERENCES customer_subscriptions (id) ON DELETE CASCADE, \n\tUNIQUE (invoice_number), \n\tFOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE SET NULL\n)"
    )
    op.execute(
        "CREATE TABLE platform_payment_integrations (\n    id BIGSERIAL NOT NULL,\n    provider VARCHAR(30) NOT NULL,\n    display_name VARCHAR(100) NOT NULL,\n    is_enabled BOOLEAN NOT NULL,\n    config JSON NOT NULL,\n    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,\n    PRIMARY KEY (id),\n    UNIQUE (provider)\n)"
    )
    op.execute(
        "INSERT INTO platform_settings (\n    platform_name, footer_html, owner_name, owner_phone, owner_phone_intl,\n    support_email, default_currency, default_language,\n    default_commission_percent, singleton, valuepayment_enabled, valuepayment_config\n) VALUES (\n    'Azadexa',\n    '<footer id=\"azadexa-platform-footer\" class=\"azadexa-platform-footer\" data-immutable=\"true\">Powered by Azadexa &mdash; Ahmad Ghannam</footer>',\n    'Ahmad Ghannam', '0562150193', '+972562150193',\n    'support@azadexa.com', 'ILS', 'ar', 0.0100, '1', true, '{}'::json\n) ON CONFLICT (singleton) DO NOTHING"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TABLE IF EXISTS platform_payment_integrations")
    bind = op.get_bind()
    for table in reversed(inspect(bind).get_table_names()):
        if table != "alembic_version":
            op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
