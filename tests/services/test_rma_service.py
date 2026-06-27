"""RMA service unit tests (wave 9)."""

from __future__ import annotations

import pytest

from catalog_svc.product_service import ProductService
from core.exceptions import ValidationError
from order.order import OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from rma_svc.rma_service import RmaService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def _paid_order(tenant):
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Returnable",
        slug="returnable",
        price="20.00",
        quantity=10,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="ret@test.com",
        shipping_address={"city": "Nablus"},
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    return order, product


def test_rma_create_and_approve(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="RMA Co", slug="rma-co", email="rma@test.com"
    )
    order, _product = _paid_order(tenant)
    oi = OrderItem.query.filter_by(order_id=order.id).first()
    svc = RmaService()
    row = svc.create_return(
        tenant_id=tenant.id,
        order_id=order.id,
        items=[{"order_item_id": oi.id, "quantity": 1}],
        reason_code="defective",
    )
    assert row.status == "requested"
    assert row.refund_amount > 0
    approved = svc.approve_return(tenant_id=tenant.id, return_id=row.id)
    assert approved.status == "approved"


def test_rma_reject_unpaid_order(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="RMA Bad", slug="rma-bad", email="rbad@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="X",
        slug="x-prod",
        price="10.00",
        quantity=1,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="u@test.com",
        shipping_address={"city": "A"},
    )
    oi = OrderItem.query.filter_by(order_id=order.id).first()
    with pytest.raises(ValidationError):
        RmaService().create_return(
            tenant_id=tenant.id,
            order_id=order.id,
            items=[{"order_item_id": oi.id, "quantity": 1}],
        )


def test_rma_list_reasons(app):
    tenant = TenantService().create_tenant(
        name="Reasons", slug="reasons-co", email="rs@test.com"
    )
    reasons = RmaService().list_reasons(tenant.id)
    assert len(reasons) >= 3
