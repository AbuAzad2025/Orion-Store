"""OMS service unit tests (wave 9)."""

from __future__ import annotations

import pytest

from catalog_svc.product_service import ProductService
from core.exceptions import ValidationError
from oms_svc.oms_service import OmsService
from order.order import OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def _paid_order(tenant):
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Ship Item",
        slug="ship-item",
        price="15.00",
        quantity=10,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=2)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="ship@test.com",
        shipping_address={"city": "Gaza"},
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    return order, product


def test_oms_fulfillment_flow(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="OMS Co", slug="oms-co", email="oms@test.com"
    )
    order, product = _paid_order(tenant)
    svc = OmsService()
    wh = svc.create_warehouse(
        tenant_id=tenant.id, name="Main", code="main", is_default=True
    )
    svc.upsert_inventory(
        tenant_id=tenant.id,
        warehouse_id=wh.id,
        product_id=product.id,
        quantity=20,
    )
    fulfillment = svc.create_fulfillment(
        tenant_id=tenant.id, order_id=order.id, warehouse_id=wh.id
    )
    assert fulfillment.status == "pending"
    shipped = svc.ship_fulfillment(
        tenant_id=tenant.id,
        fulfillment_id=fulfillment.id,
        tracking_number="TRK123",
    )
    assert shipped.status == "shipped"
    assert shipped.tracking_number == "TRK123"


def test_oms_insufficient_inventory(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="OMS Low", slug="oms-low", email="ol@test.com"
    )
    order, product = _paid_order(tenant)
    svc = OmsService()
    wh = svc.create_warehouse(tenant_id=tenant.id, name="Small", code="small")
    svc.upsert_inventory(
        tenant_id=tenant.id,
        warehouse_id=wh.id,
        product_id=product.id,
        quantity=1,
    )
    with pytest.raises(ValidationError):
        svc.create_fulfillment(
            tenant_id=tenant.id, order_id=order.id, warehouse_id=wh.id
        )
