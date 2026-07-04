"""PayPal/BNPL API tests (wave 8)."""

from __future__ import annotations

import hashlib
import hmac
import time

from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService

WEBHOOK_SECRET = "whsec_test_paypal"


def _paypal_headers(raw: bytes) -> dict[str, str]:
    ts = int(time.time())
    body_str = raw.decode("utf-8")
    signed_parts = [str(ts), ts, "webhook_id", body_str]
    signed_str = "|".join(str(p) for p in signed_parts)
    sig = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        signed_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "PAYPAL-TRANSMIT-ID": str(ts),
        "PAYPAL-TRANSMIT-TIME": str(ts),
        "PAYPAL-WEBHOOK-ID": "webhook_id",
        "PAYPAL-AUTH-ALGO": "HMAC-SHA256",
        "PAYPAL-CERT-URL": "https://example.com/cert",
        "PAYPAL-TRANSMIT-SIG": sig,
    }


def _hmac_signature(raw: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()


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
    headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
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
    headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
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
    app.config["WEBHOOK_SECRET"] = WEBHOOK_SECRET
    tenant = TenantService().create_tenant(
        name="PP WH", slug="pp-wh", email="ppwh@test.com"
    )
    raw = b'{"event_type":"PAYMENT.CAPTURE.COMPLETED"}'
    res = client.post(
        f"/webhooks/paypal/{tenant.id}",
        data=raw,
        content_type="application/json",
        headers=_paypal_headers(raw),
    )
    assert res.status_code == 200
    assert res.get_json()["received"] is True


def test_bnpl_webhook(client, app):
    app.config["WEBHOOK_SECRET"] = WEBHOOK_SECRET
    tenant = TenantService().create_tenant(
        name="BNPL WH", slug="bnpl-wh", email="bnplwh@test.com"
    )
    raw = b'{"status":"captured"}'
    sig = _hmac_signature(raw)
    res = client.post(
        f"/webhooks/bnpl/tabby/{tenant.id}",
        data=raw,
        content_type="application/json",
        headers={"X-Webhook-Signature": sig},
    )
    assert res.status_code == 200
