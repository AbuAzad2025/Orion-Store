"""Wave 6 — shipping + voucher checkout integration."""

from __future__ import annotations

from decimal import Decimal

from support.http import tenant_headers

from catalog_svc.product_service import ProductService
from discount_svc.voucher_service import VoucherService
from order.order import Order
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from platform_svc.platform_settings_service import PlatformSettingsService
from shipping_svc.shipping_service import ShippingService
from tenant_svc.tenant_service import TenantService


def test_checkout_with_shipping_and_voucher(client, app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Wave6 Store", slug="wave6-store", email="w6@test.com"
    )
    ShippingService().seed_flat_rate(tenant.id, cost="10.00")
    VoucherService().create(
        tenant_id=tenant.id,
        code="SAVE10",
        name="10% off",
        type="percentage",
        value="10",
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Wave6 Item",
        slug="wave6-item",
        price="50.00",
        quantity=3,
        is_published=True,
    )
    headers = tenant_headers(tenant.slug)
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)

    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@wave6.com",
        shipping_address={"city": "Ramallah"},
        shipping_method_code="standard",
        voucher_code="SAVE10",
    )
    assert order.subtotal == Decimal("50.00")
    assert order.discount_amount == Decimal("5.00")
    assert order.shipping_cost == Decimal("10.00")
    assert order.total == Decimal("55.00")

    methods = client.get("/api/v1/shipping/methods", headers=headers)
    assert methods.status_code == 200
    assert methods.get_json()["methods"]

    validate = client.get(
        "/api/v1/vouchers/SAVE10/validate?subtotal=50",
        headers=headers,
    )
    assert validate.status_code == 200
    assert validate.get_json()["voucher"]["discount_amount"] == "5.00"


def test_free_shipping_voucher_zeros_shipping(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Free V", slug="free-v", email="fv@test.com"
    )
    ShippingService().seed_flat_rate(tenant.id, cost="20.00")
    VoucherService().create(
        tenant_id=tenant.id,
        code="FREESHIP",
        name="Free shipping",
        type="fixed_amount",
        value="0",
        is_free_shipping=True,
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Item",
        slug="item-fs",
        price="30.00",
        quantity=1,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="fs@test.com",
        shipping_address={"city": "Gaza"},
        shipping_method_code="standard",
        voucher_code="FREESHIP",
    )
    assert order.shipping_cost == Decimal("0")
    row = Order.query.filter_by(id=order.id).first()
    assert row.discount_code == "FREESHIP"
