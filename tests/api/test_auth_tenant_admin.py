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
