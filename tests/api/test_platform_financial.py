"""Wave 5 platform financial report API tests."""

from __future__ import annotations

from decimal import Decimal

from support.http import tenant_headers

from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService


def test_store_financial_report(client, app, platform_admin_headers):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Finance Store", slug="finance-store", email="fin@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Item",
        slug="item",
        price="20.00",
        quantity=2,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Gaza"},
    )
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )

    resp = client.get(
        f"/api/v1/platform/stores/{tenant.id}/financial-report",
        headers=platform_admin_headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["tenant"]["slug"] == "finance-store"
    assert body["summary"]["orders_paid"] == 1
    assert Decimal(body["summary"]["total_inbound"]) >= Decimal("0")


def test_storefront_public_products(client, app):
    tenant = TenantService().create_tenant(
        name="Public", slug="public-store", email="pub@test.com"
    )
    ProductService().create(
        tenant_id=tenant.id,
        name="Visible",
        slug="visible",
        price="5.00",
        quantity=1,
        is_published=True,
    )
    headers = tenant_headers(tenant.slug)
    listed = client.get("/api/v1/store/products", headers=headers)
    assert listed.status_code == 200
    assert len(listed.get_json()["products"]) == 1

    detail = client.get("/api/v1/store/products/visible", headers=headers)
    assert detail.status_code == 200
    assert detail.get_json()["product"]["slug"] == "visible"
