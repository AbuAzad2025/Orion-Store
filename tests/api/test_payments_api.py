"""Payments and webhooks API tests (wave 4)."""

from __future__ import annotations

from support.http import auth_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


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
    headers = auth_headers(admin, tenant_id=tenant.slug)
    response = client.post(
        f"/api/v1/payments/orders/{order.public_id}/pay",
        headers=headers,
        json={"payment_method": "cod"},
    )
    assert response.status_code == 200
    assert response.get_json()["order"]["payment_status"] == "paid"


def test_stripe_webhook_endpoint(client):
    response = client.post(
        "/webhooks/stripe/1",
        json={"type": "payment_intent.succeeded"},
    )
    assert response.status_code == 200
    assert response.get_json()["received"] is True


def test_stripe_webhook_ignored_event(client):
    response = client.post(
        "/webhooks/stripe/1",
        json={"type": "charge.refunded"},
    )
    assert response.status_code == 200
    assert response.get_json().get("ignored")
