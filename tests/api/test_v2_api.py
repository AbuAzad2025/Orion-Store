from __future__ import annotations

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from feature_flag_svc.feature_flag_service import FeatureFlagService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def setup(app):
    PlatformSettingsService().ensure_seeded()
    FeatureFlagService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="V2 API", slug="v2-api", email="v2api@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@v2api.com",
        password="password123",
        is_admin=True,
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="V2 API Product",
        slug="v2-api-product",
        price="19.99",
        quantity=100,
        is_published=True,
    )
    return tenant, auth_headers(admin, app=app, tenant_id=tenant.slug), product


def test_subscription_plan_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/subscriptions/plans",
        headers=headers,
        json={
            "name": "Pro Plan",
            "code": "pro",
            "billing_period_days": 30,
            "price": "29.99",
            "trial_period_days": 14,
        },
    )
    assert res.status_code == 201
    assert res.get_json()["plan"]["name"] == "Pro Plan"

    plan_id = res.get_json()["plan"]["id"]
    res = client.post(
        "/api/v1/subscriptions/subscribe",
        headers=headers,
        json={
            "plan_id": plan_id,
            "customer_email": "sub@test.com",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["subscription"]["customer_email"] == "sub@test.com"


def test_store_credit_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/store-credit/add",
        headers=headers,
        json={
            "customer_email": "buyer@test.com",
            "amount": "50.00",
            "reason": "Promo",
        },
    )
    assert res.status_code == 200
    assert float(res.get_json()["credit"]["balance"]) == 50.00

    balance = client.get(
        "/api/v1/store-credit/balance?customer_email=buyer@test.com", headers=headers
    )
    assert balance.status_code == 200
    assert float(balance.get_json()["balance"]) == 50.00

    use = client.post(
        "/api/v1/store-credit/deduct",
        headers=headers,
        json={
            "customer_email": "buyer@test.com",
            "amount": "20.00",
        },
    )
    assert use.status_code == 200
    assert float(use.get_json()["credit"]["balance"]) == 30.00


def test_draft_orders_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/draft-orders", headers=headers, json={"notes": "Test draft"}
    )
    assert res.status_code == 201
    draft_id = res.get_json()["draft_order"]["id"]

    res = client.post(
        f"/api/v1/draft-orders/{draft_id}/items",
        headers=headers,
        json={
            "product_id": product.id,
            "quantity": 2,
        },
    )
    assert res.status_code == 201

    res = client.post(
        f"/api/v1/draft-orders/{draft_id}/convert",
        headers=headers,
        json={
            "customer_email": "cust@test.com",
        },
    )
    assert res.status_code == 201
    assert "order" in res.get_json()


def test_tax_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/tax/jurisdictions",
        headers=headers,
        json={
            "code": "CA-STATE",
            "name": "CA State",
            "country_code": "US",
            "region": "CA",
        },
    )
    assert res.status_code == 201
    jur_id = res.get_json()["jurisdiction"]["id"]

    res = client.post(
        f"/api/v1/tax/jurisdictions/{jur_id}/rates",
        headers=headers,
        json={"rate": "0.0725"},
    )
    assert res.status_code == 201


def test_bundles_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/bundles",
        headers=headers,
        json={
            "name": "Combo Pack",
            "slug": "combo-pack",
            "bundle_price": "24.99",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["bundle"]["name"] == "Combo Pack"


def test_metafields_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/metafields/definitions",
        headers=headers,
        json={
            "owner_type": "product",
            "key": "material",
            "label": "Material",
            "field_type": "string",
        },
    )
    assert res.status_code == 201
    def_id = res.get_json()["definition"]["id"]

    res = client.post(
        "/api/v1/metafields/values",
        headers=headers,
        json={
            "definition_id": def_id,
            "owner_id": product.id,
            "value": "cotton",
        },
    )
    assert res.status_code == 200

    res = client.get(f"/api/v1/metafields/product/{product.id}", headers=headers)
    assert res.status_code == 200


def test_bopis_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/bopis/locations",
        headers=headers,
        json={
            "code": "DTLA",
            "name": "Downtown Store",
            "address": {
                "street": "123 Main St",
                "city": "LA",
                "region": "CA",
                "postal_code": "90001",
                "country": "US",
            },
        },
    )
    assert res.status_code == 201
    assert res.get_json()["location"]["name"] == "Downtown Store"


def test_currency_api(client, app, setup):
    tenant, headers, product = setup
    super_admin = AuthService().register_super_admin(
        email="su@currency.test", password="su123456"
    )
    su_headers = auth_headers(super_admin, app=app)
    res = client.post(
        "/api/v1/currency/rates",
        headers=su_headers,
        json={
            "from_currency": "USD",
            "to_currency": "EUR",
            "rate": "0.85",
        },
    )
    assert res.status_code == 201
    assert float(res.get_json()["rate"]["rate"]) == 0.85

    res = client.get("/api/v1/currency/convert?amount=100&from=USD&to=EUR")
    assert res.status_code == 200
    assert float(res.get_json()["result"]) == 85.00


def test_import_export_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/import-export/jobs",
        headers=headers,
        json={
            "job_type": "export",
            "entity_type": "products",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["job"]["job_type"] == "export"


def test_stock_notifications_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/stock-notifications",
        headers=headers,
        json={
            "customer_email": "notify@test.com",
            "product_id": product.id,
        },
    )
    assert res.status_code == 201
    assert res.get_json()["notification"]["customer_email"] == "notify@test.com"


def test_app_platform_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/app-platform/apps",
        headers=headers,
        json={
            "name": "Test App",
            "redirect_uris": ["https://app.com/callback"],
            "scopes": "read_products",
        },
    )
    assert res.status_code == 201
    app_id = res.get_json()["app"]["id"]

    res = client.post(
        f"/api/v1/app-platform/apps/{app_id}/install",
        headers=headers,
        json={"installed_by": 1},
    )
    assert res.status_code == 201

    res = client.post(
        "/api/v1/app-platform/sandboxes",
        headers=headers,
        json={
            "slug": "sandbox-1",
            "name": "Test Sandbox",
            "expires_at": "2027-01-01",
        },
    )
    assert res.status_code == 201


def test_fraud_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/fraud/rules",
        headers=headers,
        json={
            "name": "High Value",
            "rule_type": "amount",
            "operator": "gt",
            "threshold_value": "1000",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["rule"]["name"] == "High Value"

    res = client.post(
        "/api/v1/fraud/reviews",
        headers=headers,
        json={
            "order_id": 1,
            "risk_score": 85,
        },
    )
    assert res.status_code == 201
    assert res.get_json()["review"]["risk_score"] == 85


def test_compliance_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/compliance/consent",
        headers=headers,
        json={
            "customer_email": "user@test.com",
            "consent_type": "marketing",
            "granted": True,
        },
    )
    assert res.status_code == 201

    res = client.post(
        "/api/v1/compliance/data-requests",
        headers=headers,
        json={
            "customer_email": "user@test.com",
            "request_type": "access",
        },
    )
    assert res.status_code == 201

    res = client.put(
        "/api/v1/compliance/cookie-settings",
        headers=headers,
        json={
            "banner_message": "We use cookies",
            "is_active": True,
        },
    )
    assert res.status_code == 200

    res = client.post(
        "/api/v1/compliance/sso",
        headers=headers,
        json={
            "provider_type": "oidc",
            "client_id": "abc",
            "client_secret": "secret",
        },
    )
    assert res.status_code == 201


def test_workflow_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/workflow/definitions",
        headers=headers,
        json={
            "name": "Order Confirm",
            "trigger_event": "order.placed",
            "actions": [{"type": "send_email"}],
        },
    )
    assert res.status_code == 201
    assert res.get_json()["definition"]["name"] == "Order Confirm"

    res = client.get("/api/v1/workflow/definitions", headers=headers)
    assert res.status_code == 200


def test_search_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/search/synonyms",
        headers=headers,
        json={
            "term": "laptop",
            "synonyms": ["notebook", "ultrabook"],
        },
    )
    assert res.status_code == 201

    res = client.post(
        "/api/v1/search/redirects",
        headers=headers,
        json={
            "query_term": "fb",
            "redirect_url": "/products/facebook",
        },
    )
    assert res.status_code == 201

    res = client.post(
        "/api/v1/search/boosts",
        headers=headers,
        json={
            "product_id": product.id,
            "boost_factor": 2,
            "query_keyword": "featured",
        },
    )
    assert res.status_code == 201


def test_affiliates_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/affiliates/programs",
        headers=headers,
        json={
            "name": "Gold",
            "code": "GOLD",
            "commission_type": "percentage",
            "commission_value": "15",
        },
    )
    assert res.status_code == 201

    res = client.post(
        "/api/v1/affiliates/register",
        headers=headers,
        json={
            "program_id": 1,
            "email": "aff@test.com",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["affiliate"]["email"] == "aff@test.com"


def test_gift_registries_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/gift-registries",
        headers=headers,
        json={
            "customer_email": "gifter@test.com",
            "registry_name": "Wedding",
            "event_type": "wedding",
            "is_public": True,
        },
    )
    assert res.status_code == 201
    slug = res.get_json()["registry"]["slug"]
    assert len(slug) > 0


def test_dropship_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/dropship/suppliers",
        headers=headers,
        json={
            "name": "FastShip",
            "contact_email": "orders@fastship.com",
            "fulfillment_time_days": 3,
        },
    )
    assert res.status_code == 201

    res = client.post(
        "/api/v1/dropship/pod",
        headers=headers,
        json={
            "provider": "printful",
            "api_key": "key123",
        },
    )
    assert res.status_code == 201


def test_schema_markup_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/schema-markup",
        headers=headers,
        json={
            "product_id": product.id,
            "schema_type": "Product",
            "json_ld": {"name": "Test Product", "price": "29.99"},
        },
    )
    assert res.status_code == 201
    assert res.get_json()["markup"]["schema_type"] == "Product"


def test_accessibility_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/accessibility/audits",
        headers=headers,
        json={
            "page_url": "/products",
            "score": 92,
            "issues": {"contrast": ["issue"]},
        },
    )
    assert res.status_code == 201

    res = client.get("/api/v1/accessibility/audits", headers=headers)
    assert res.status_code == 200


def test_live_chat_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post(
        "/api/v1/live-chat/sessions",
        headers=headers,
        json={
            "customer_email": "chat@test.com",
        },
    )
    assert res.status_code == 201
    session_id = res.get_json()["session"]["id"]

    res = client.post(
        f"/api/v1/live-chat/sessions/{session_id}/messages",
        headers=headers,
        json={
            "sender_type": "customer",
            "message": "Hello!",
        },
    )
    assert res.status_code == 201

    res = client.get(
        f"/api/v1/live-chat/sessions/{session_id}/messages", headers=headers
    )
    assert res.status_code == 200


def test_reconciliation_api(client, app, setup):
    tenant, headers, product = setup
    res = client.post("/api/v1/reconciliation/runs", headers=headers)
    assert res.status_code == 201
    run_id = res.get_json()["run"]["id"]

    res = client.post(
        f"/api/v1/reconciliation/runs/{run_id}/items",
        headers=headers,
        json={
            "financial_event_id": 1,
            "expected_amount": "100.00",
            "actual_amount": "100.00",
        },
    )
    assert res.status_code == 201

    res = client.post(f"/api/v1/reconciliation/runs/{run_id}/complete", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["run"]["status"] == "completed"


def test_audit_api(client, app, setup):
    tenant, headers, product = setup
    super_admin = AuthService().register_super_admin(
        email="su@audit.test", password="su123456"
    )
    su_headers = auth_headers(super_admin, app=app)
    res = client.post(
        "/api/v1/audit/logs",
        headers=headers,
        json={
            "user_id": 1,
            "action": "user.login",
            "details": {"ip": "1.2.3.4"},
        },
    )
    assert res.status_code == 201

    res = client.get("/api/v1/audit/logs", headers=su_headers)
    assert res.status_code == 200


def test_oms_ext_api(client, app, setup):
    tenant, headers, product = setup
    res = client.get("/api/v1/oms-ext/warehouses", headers=headers)
    assert res.status_code == 200
