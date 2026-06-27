"""Wave 8 PayPal and BNPL payment E2E tests."""

from __future__ import annotations

from support.http import tenant_headers

from bnpl_svc.bnpl_service import BnplService
from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def _checkout_order(tenant, client=None):
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Pay Item",
        slug="pay-item",
        price="30.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    return CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
    )


def test_paypal_payment_full_flow(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="PayPal Store", slug="paypal-store", email="pps@test.com"
    )
    GatewayService().upsert_paypal(
        tenant_id=tenant.id,
        client_id="cid",
        client_secret="sec",
        is_sandbox=True,
    )
    order = _checkout_order(tenant)
    headers = tenant_headers(tenant.slug)
    pay = client.post(
        f"/api/v1/store/orders/{order.public_id}/pay",
        headers=headers,
        json={"payment_method": "paypal"},
    )
    assert pay.status_code == 200
    body = pay.get_json()
    assert body["order"]["payment_status"] == "paid"
    assert body["payment"]["payment_method"] == "paypal"
    assert body["commission_ledger_id"] is not None


def test_bnpl_tabby_payment_full_flow(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Tabby Store", slug="tabby-store", email="tabby@test.com"
    )
    BnplService().upsert_provider(
        tenant_id=tenant.id,
        provider="tabby",
        merchant_id="m1",
        api_key="k1",
        is_enabled=True,
    )
    order = _checkout_order(tenant)
    headers = tenant_headers(tenant.slug)
    pay = client.post(
        f"/api/v1/store/orders/{order.public_id}/pay",
        headers=headers,
        json={"payment_method": "bnpl_tabby"},
    )
    assert pay.status_code == 200
    body = pay.get_json()
    assert body["order"]["payment_status"] == "paid"
    assert body["financial_event"]["event_type"] == "bnpl_capture"
    assert body["bnpl_transaction"]["provider"] == "tabby"
