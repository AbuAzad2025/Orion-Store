"""Payments and webhooks API tests (wave 4)."""

from __future__ import annotations

import hashlib
import hmac
import time

from support.http import auth_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService

WEBHOOK_SECRET = "whsec_test_stripe"


def _stripe_signature(raw: bytes) -> str:
    ts = int(time.time())
    to_sign = f"{ts}.{raw.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(WEBHOOK_SECRET.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _webhook_headers(raw: bytes) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Stripe-Signature": _stripe_signature(raw),
    }


def test_payments_api_pay_order(client, app):
    PlatformSettingsService().ensure_seeded()
    tenants = TenantService()
    auth = AuthService()
    tenant = tenants.create_tenant(
        name="Pay API", slug="pay-api", email="payapi@test.com"
    )
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@payapi.com",
        password="password123",
        is_admin=True,
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="API Product",
        slug="api-product",
        price="12.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@payapi.com",
        shipping_address={},
    )
    headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
    response = client.post(
        f"/api/v1/payments/orders/{order.public_id}/pay",
        headers=headers,
        json={"payment_method": "cod"},
    )
    assert response.status_code == 200
    assert response.get_json()["order"]["payment_status"] == "paid"


def _create_test_tenant() -> tuple:
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="WH Test", slug="wh-test", email="wh@test.com"
    )
    return tenant


def test_stripe_webhook_endpoint(client, app):
    app.config["WEBHOOK_SECRET"] = WEBHOOK_SECRET
    tenant = _create_test_tenant()
    raw = b'{"type":"payment_intent.succeeded"}'
    response = client.post(
        f"/webhooks/stripe/{tenant.id}",
        data=raw,
        content_type="application/json",
        headers=_webhook_headers(raw),
    )
    assert response.status_code == 200
    assert response.get_json()["received"] is True


def test_stripe_webhook_ignored_event(client, app):
    app.config["WEBHOOK_SECRET"] = WEBHOOK_SECRET
    tenant = _create_test_tenant()
    raw = b'{"type":"charge.refunded"}'
    response = client.post(
        f"/webhooks/stripe/{tenant.id}",
        data=raw,
        content_type="application/json",
        headers=_webhook_headers(raw),
    )
    assert response.status_code == 200
    assert response.get_json().get("ignored")


def test_stripe_webhook_bad_signature(client, app):
    app.config["WEBHOOK_SECRET"] = WEBHOOK_SECRET
    tenant = _create_test_tenant()
    response = client.post(
        f"/webhooks/stripe/{tenant.id}",
        json={"type": "payment_intent.succeeded"},
        headers={"Stripe-Signature": "t=1,v1=bad"},
    )
    assert response.status_code == 400
    assert "Invalid signature" in response.get_json()["error"]


def test_stripe_webhook_unknown_tenant(client, app):
    app.config["WEBHOOK_SECRET"] = WEBHOOK_SECRET
    raw = b'{"type":"payment_intent.succeeded"}'
    response = client.post(
        "/webhooks/stripe/99999",
        data=raw,
        content_type="application/json",
        headers=_webhook_headers(raw),
    )
    assert response.status_code == 404
