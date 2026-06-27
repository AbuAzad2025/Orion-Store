"""PayPal/BNPL API tests (wave 8)."""

from __future__ import annotations

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_paypal_connect_and_payment_methods(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="PP API", slug="pp-api", email="ppa@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@ppa.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)
    connect = client.post(
        "/api/v1/tenant/gateways/paypal",
        headers=headers,
        json={
            "client_id": "cid",
            "client_secret": "csec",
            "is_sandbox": True,
        },
    )
    assert connect.status_code == 200
    assert connect.get_json()["gateway"]["provider"] == "paypal"

    store_headers = tenant_headers(tenant.slug)
    methods = client.get("/api/v1/store/payment-methods", headers=store_headers)
    assert methods.status_code == 200
    codes = [m["code"] for m in methods.get_json()["payment_methods"]]
    assert "paypal" in codes


def test_bnpl_provider_upsert(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="BNPL API", slug="bnpl-api", email="bapi@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@bapi.com",
        password="password123",
        is_admin=True,
    )
    headers = auth_headers(admin, tenant_id=tenant.slug)
    upsert = client.put(
        "/api/v1/tenant/bnpl/providers/tabby",
        headers=headers,
        json={
            "merchant_id": "tabby-merchant",
            "api_key": "tabby-key",
            "is_enabled": True,
            "is_sandbox": True,
        },
    )
    assert upsert.status_code == 200
    body = upsert.get_json()["provider"]
    assert body["provider"] == "tabby"
    assert body["is_enabled"] is True

    listed = client.get("/api/v1/tenant/bnpl/providers", headers=headers)
    assert listed.status_code == 200
    providers = listed.get_json()["providers"]
    tabby = next(p for p in providers if p["provider"] == "tabby")
    assert tabby["merchant_id"] == "tabby-merchant"


def test_paypal_webhook(client, app):
    res = client.post(
        "/webhooks/paypal/1",
        json={"event_type": "PAYMENT.CAPTURE.COMPLETED"},
    )
    assert res.status_code == 200
    assert res.get_json()["received"] is True


def test_bnpl_webhook(client, app):
    res = client.post(
        "/webhooks/bnpl/tabby/1",
        json={"status": "captured"},
    )
    assert res.status_code == 200
