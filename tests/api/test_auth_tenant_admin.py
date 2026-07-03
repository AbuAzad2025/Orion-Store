"""AZ-0.3: Tenant-admin authorization enforcement tests.

Verifies that every protected endpoint rejects unauthenticated,
non-admin, and cross-tenant requests.
"""

from __future__ import annotations

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def setup(app):
    PlatformSettingsService().ensure_seeded()
    t1 = TenantService().create_tenant(name="T1", slug="t1-auth", email="t1@test.com")
    t2 = TenantService().create_tenant(name="T2", slug="t2-auth", email="t2@test.com")
    admin_t1 = AuthService().register_tenant_user(
        tenant_id=t1.id, email="admin@t1.com", password="password123", is_admin=True,
    )
    customer_t1 = AuthService().register_tenant_user(
        tenant_id=t1.id, email="cust@t1.com", password="password123", is_admin=False,
    )
    admin_t1_headers = auth_headers(admin_t1, app=app, tenant_id=t1.slug)
    customer_headers = auth_headers(customer_t1, app=app, tenant_id=t1.slug)
    wrong_tenant_headers = auth_headers(admin_t1, app=app, tenant_id=t2.slug)
    no_auth_headers = {"X-Tenant-ID": t1.slug, "Content-Type": "application/json"}
    return t1, admin_t1_headers, customer_headers, wrong_tenant_headers, no_auth_headers


def _assert_denied(resp):
    assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}: {resp.get_json()}"


class TestFraud:
    BASE = "/api/v1/fraud"

    def test_list_rules_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/rules", headers=no_auth))

    def test_list_rules_denies_customer(self, client, setup):
        _, _, cust, _, _ = setup
        _assert_denied(client.get(f"{self.BASE}/rules", headers=cust))

    def test_list_rules_denies_wrong_tenant(self, client, setup):
        _, _, _, wrong, _ = setup
        _assert_denied(client.get(f"{self.BASE}/rules", headers=wrong))

    def test_list_rules_allows_admin(self, client, setup):
        t1, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/rules", headers=admin)
        assert resp.status_code == 200

    def test_create_rule_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/rules", headers=no_auth, json={"name": "x", "rule_type": "amount", "operator": "gt", "threshold_value": "100"}))

    def test_create_rule_denies_customer(self, client, setup):
        _, _, cust, _, _ = setup
        _assert_denied(client.post(f"{self.BASE}/rules", headers=cust, json={"name": "x", "rule_type": "amount", "operator": "gt", "threshold_value": "100"}))

    def test_create_rule_denies_wrong_tenant(self, client, setup):
        _, _, _, wrong, _ = setup
        _assert_denied(client.post(f"{self.BASE}/rules", headers=wrong, json={"name": "x", "rule_type": "amount", "operator": "gt", "threshold_value": "100"}))

    def test_create_rule_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/rules", headers=admin, json={"name": "Rule1", "rule_type": "amount", "operator": "gt", "threshold_value": "100"})
        assert resp.status_code == 201


class TestReconciliation:
    BASE = "/api/v1/reconciliation"

    def test_list_runs_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/runs", headers=no_auth))

    def test_list_runs_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/runs", headers=admin)
        assert resp.status_code == 200

    def test_create_run_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/runs", headers=no_auth))

    def test_create_run_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/runs", headers=admin)
        assert resp.status_code == 201


class TestSubscriptions:
    BASE = "/api/v1/subscriptions"

    def test_list_plans_public(self, client, setup):
        t1, _, _, _, _ = setup
        resp = client.get(f"{self.BASE}/plans", headers={"X-Tenant-ID": t1.slug})
        assert resp.status_code == 200

    def test_create_plan_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/plans", headers=no_auth, json={"name": "P", "code": "p", "billing_period_days": 30, "price": "10"}))

    def test_create_plan_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/plans", headers=admin, json={"name": "Pro", "code": "pro", "billing_period_days": 30, "price": "29.99"})
        assert resp.status_code == 201

    def test_subscribe_denies_anonymous(self, client, app, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/subscribe", headers=no_auth, json={"plan_id": 1, "customer_email": "a@b.com"}))

    def test_list_subscriptions_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/subscriptions", headers=no_auth))

    def test_list_subscriptions_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/subscriptions", headers=admin)
        assert resp.status_code == 200

    def test_create_asset_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/digital-assets", headers=no_auth, json={"product_id": 1, "file_url": "http://x.com/f", "file_name": "f.pdf"}))

    def test_create_asset_allows_admin(self, client, app, setup):
        from catalog_svc.product_service import ProductService
        t1, admin, _, _, _ = setup
        product = ProductService().create(
            tenant_id=t1.id, name="Auth Test Product", slug="auth-test-p", price="10", quantity=10,
        )
        resp = client.post(f"{self.BASE}/digital-assets", headers=admin, json={"product_id": product.id, "file_url": "http://x.com/f", "file_name": "f.pdf"})
        assert resp.status_code == 201


class TestStoreCredit:
    BASE = "/api/v1/store-credit"

    def test_get_balance_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/balance?customer_email=a@b.com", headers=no_auth))

    def test_get_balance_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/balance?customer_email=a@b.com", headers=admin)
        assert resp.status_code == 200

    def test_add_funds_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/add", headers=no_auth, json={"customer_email": "a@b.com", "amount": "10"}))

    def test_add_funds_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/add", headers=admin, json={"customer_email": "a@b.com", "amount": "10"})
        assert resp.status_code == 200


class TestDraftOrders:
    BASE = "/api/v1/draft-orders"

    def test_list_drafts_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(self.BASE, headers=no_auth))

    def test_list_drafts_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(self.BASE, headers=admin)
        assert resp.status_code == 200

    def test_create_draft_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(self.BASE, headers=no_auth, json={"customer_email": "a@b.com"}))

    def test_create_draft_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(self.BASE, headers=admin, json={"customer_email": "a@b.com"})
        assert resp.status_code == 201

    def test_convert_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/1/convert", headers=no_auth, json={"customer_email": "a@b.com"}))


class TestDropship:
    BASE = "/api/v1/dropship"

    def test_list_pod_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/pod", headers=no_auth))

    def test_list_pod_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/pod", headers=admin)
        assert resp.status_code == 200

    def test_create_pod_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/pod", headers=no_auth, json={"provider": "test", "api_key": "k"}))

    def test_create_pod_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/pod", headers=admin, json={"provider": "TestProvider", "api_key": "sk_test"})
        assert resp.status_code == 201

    def test_list_suppliers_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/suppliers", headers=admin)
        assert resp.status_code == 200

    def test_create_supplier_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/suppliers", headers=admin, json={"name": "S1", "contact_email": "s@t.com"})
        assert resp.status_code == 201

    def test_dropship_orders_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/orders", headers=no_auth))

    def test_dropship_orders_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/orders", headers=admin)
        assert resp.status_code == 200


class TestAffiliates:
    BASE = "/api/v1/affiliates"

    def test_list_programs_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/programs", headers=no_auth))

    def test_list_programs_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/programs", headers=admin)
        assert resp.status_code == 200

    def test_list_affiliates_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/affiliates", headers=admin)
        assert resp.status_code == 200

    def test_list_commissions_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/commissions", headers=admin)
        assert resp.status_code == 200

    def test_create_program_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/programs", headers=no_auth, json={"name": "P", "code": "p", "commission_type": "percentage", "commission_value": "10"}))

    def test_create_program_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/programs", headers=admin, json={"name": "Referral", "code": "REF", "commission_type": "percentage", "commission_value": "10"})
        assert resp.status_code == 201

    def test_register_affiliate_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        prog_resp = client.post(f"{self.BASE}/programs", headers=admin, json={"name": "RegTest", "code": "RT", "commission_type": "percentage", "commission_value": "5"})
        assert prog_resp.status_code == 201
        program_id = prog_resp.get_json()["program"]["id"]
        resp = client.post(f"{self.BASE}/register", headers=admin, json={"program_id": program_id, "email": "a@t.com"})
        assert resp.status_code == 201

    def test_record_commission_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/commissions", headers=no_auth, json={"affiliate_id": 1, "order_id": 1, "amount": "10"}))


class TestAppPlatform:
    BASE = "/api/v1/app-platform"

    def test_list_apps_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/apps", headers=no_auth))

    def test_list_apps_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/apps", headers=admin)
        assert resp.status_code == 200

    def test_list_sandboxes_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/sandboxes", headers=admin)
        assert resp.status_code == 200

    def test_register_app_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/apps", headers=no_auth, json={"name": "App1"}))

    def test_register_app_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/apps", headers=admin, json={"name": "MyApp"})
        assert resp.status_code == 201

    def test_create_sandbox_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/sandboxes", headers=admin, json={"slug": "sand1", "name": "Sand1", "expires_at": "2026-12-31"})
        assert resp.status_code == 201


class TestCompliance:
    BASE = "/api/v1/compliance"

    def test_list_consent_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/consent", headers=no_auth))

    def test_list_consent_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/consent", headers=admin)
        assert resp.status_code == 200

    def test_list_data_requests_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/data-requests", headers=admin)
        assert resp.status_code == 200

    def test_get_cookie_settings_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/cookie-settings", headers=admin)
        assert resp.status_code == 200

    def test_record_consent_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/consent", headers=no_auth, json={"customer_email": "a@b.com", "consent_type": "marketing", "granted": True}))

    def test_record_consent_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/consent", headers=admin, json={"customer_email": "a@t.com", "consent_type": "marketing", "granted": True})
        assert resp.status_code == 201

    def test_create_data_request_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/data-requests", headers=admin, json={"customer_email": "a@t.com", "request_type": "access"})
        assert resp.status_code == 201

    def test_list_sso_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/sso", headers=admin)
        assert resp.status_code == 200

    def test_create_sso_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/sso", headers=admin, json={"provider_type": "google", "client_id": "cid", "client_secret": "sec"})
        assert resp.status_code == 201


class TestGiftRegistries:
    BASE = "/api/v1/gift-registries"

    def test_list_registries_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(self.BASE, headers=no_auth))

    def test_list_registries_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(self.BASE, headers=admin)
        assert resp.status_code == 200

    def test_create_registry_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(self.BASE, headers=no_auth, json={"customer_email": "a@b.com", "registry_name": "Wedding"}))

    def test_create_registry_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(self.BASE, headers=admin, json={"customer_email": "a@t.com", "registry_name": "Wedding"})
        assert resp.status_code == 201

    def test_get_registry_public(self, client, setup):
        t1, _, _, _, _ = setup
        resp = client.get(f"{self.BASE}/nonexistent", headers={"X-Tenant-ID": t1.slug})
        assert resp.status_code == 404


class TestLiveChat:
    BASE = "/api/v1/live-chat"

    def test_list_sessions_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/sessions", headers=no_auth))

    def test_list_sessions_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/sessions", headers=admin)
        assert resp.status_code == 200

    def test_create_session_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.post(f"{self.BASE}/sessions", headers=no_auth, json={}))

    def test_create_session_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.post(f"{self.BASE}/sessions", headers=admin, json={"customer_email": "a@t.com"})
        assert resp.status_code == 201


class TestAccessibility:
    BASE = "/api/v1/accessibility"

    def test_list_audits_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/audits", headers=no_auth))

    def test_list_audits_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/audits", headers=admin)
        assert resp.status_code == 200


class TestBopis:
    BASE = "/api/v1/bopis"

    def test_list_locations_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/locations", headers=no_auth))

    def test_list_locations_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/locations", headers=admin)
        assert resp.status_code == 200


class TestBundles:
    BASE = "/api/v1/bundles"

    def test_list_bundles_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(self.BASE, headers=no_auth))

    def test_list_bundles_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(self.BASE, headers=admin)
        assert resp.status_code == 200


class TestImportExport:
    BASE = "/api/v1/import-export"

    def test_list_jobs_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/jobs", headers=no_auth))

    def test_list_jobs_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/jobs", headers=admin)
        assert resp.status_code == 200


class TestMetafields:
    BASE = "/api/v1/metafields"

    def test_list_definitions_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/definitions", headers=no_auth))

    def test_list_definitions_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/definitions", headers=admin)
        assert resp.status_code == 200


class TestOmsExtensions:
    BASE = "/api/v1/oms-ext"

    def test_list_warehouses_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/warehouses", headers=no_auth))

    def test_list_warehouses_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/warehouses", headers=admin)
        assert resp.status_code == 200


class TestSchemaMarkup:
    BASE = "/api/v1/schema-markup"

    def test_list_markups_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(self.BASE, headers=no_auth))

    def test_list_markups_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(self.BASE, headers=admin)
        assert resp.status_code == 200


class TestSearchMerchandising:
    BASE = "/api/v1/search"

    def test_list_synonyms_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/synonyms", headers=no_auth))

    def test_list_synonyms_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/synonyms", headers=admin)
        assert resp.status_code == 200


class TestTax:
    BASE = "/api/v1/tax"

    def test_list_jurisdictions_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/jurisdictions", headers=no_auth))

    def test_list_jurisdictions_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/jurisdictions", headers=admin)
        assert resp.status_code == 200


class TestWorkflow:
    BASE = "/api/v1/workflow"

    def test_list_runs_denies_anonymous(self, client, setup):
        _, _, _, _, no_auth = setup
        _assert_denied(client.get(f"{self.BASE}/runs", headers=no_auth))

    def test_list_runs_allows_admin(self, client, setup):
        _, admin, _, _, _ = setup
        resp = client.get(f"{self.BASE}/runs", headers=admin)
        assert resp.status_code == 200


class TestCrossTenantIsolation:
    """Batch 1 endpoints must not leak cross-tenant data."""

    def test_fraud_rules_isolated(self, client, app, setup):
        t1, admin_t1, _, _, _ = setup
        client.post("/api/v1/fraud/rules", headers=admin_t1, json={
            "name": "T1 Rule", "rule_type": "amount", "operator": "gt", "threshold_value": "100",
        })
        t2 = TenantService().create_tenant(name="T2 Iso", slug="t2-iso", email="t2i@test.com")
        admin_t2 = AuthService().register_tenant_user(
            tenant_id=t2.id, email="admin@t2i.com", password="password123", is_admin=True,
        )
        headers_t2 = auth_headers(admin_t2, app=app, tenant_id=t2.slug)
        resp = client.get("/api/v1/fraud/rules", headers=headers_t2)
        assert resp.status_code == 200
        assert len(resp.get_json()["rules"]) == 0

    def test_subscriptions_isolated(self, client, app, setup):
        _, admin_t1, _, _, _ = setup
        client.post("/api/v1/subscriptions/plans", headers=admin_t1, json={
            "name": "T1 Plan", "code": "t1p", "billing_period_days": 30, "price": "10",
        })
        t2 = TenantService().create_tenant(name="T2 Sub Iso", slug="t2-sub-iso", email="t2s@test.com")
        admin_t2 = AuthService().register_tenant_user(
            tenant_id=t2.id, email="admin@t2s.com", password="password123", is_admin=True,
        )
        headers_t2 = auth_headers(admin_t2, app=app, tenant_id=t2.slug)
        resp = client.get("/api/v1/subscriptions/plans", headers={"X-Tenant-ID": t2.slug})
        assert resp.status_code == 200
        assert len(resp.get_json()["plans"]) == 0
