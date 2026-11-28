"""Round-7/8 regression: RMA cannot refund for free or double-count a line."""

from __future__ import annotations

import pytest

from catalog_svc.product_service import ProductService
from core.exceptions import ValidationError
from order.order import OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from payment.refund import Refund
from returns.merchandise_return import MerchandiseReturn, ReturnItem
from rma_svc.rma_service import RmaService
from tenant_svc.tenant_service import TenantService


def _paid_order_without_payment(*, quantity=2):
    tenant = TenantService().create_tenant(
        name="RMA Store", slug="rma-store", email="rma@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Returnable",
        slug="returnable",
        price="10.00",
        quantity=10,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=quantity)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
    )
    order.payment_status = "paid"
    db.session.commit()
    oi = OrderItem.query.filter_by(order_id=order.id).one()
    return tenant, product, order, oi


def test_complete_return_without_payment_fails_closed(app):
    tenant, product, order, oi = _paid_order_without_payment()
    svc = RmaService()
    row = svc.create_return(
        tenant_id=tenant.id,
        order_id=order.id,
        items=[{"order_item_id": oi.id, "quantity": 1}],
        reason_code="defective",
    )
    svc.approve_return(tenant_id=tenant.id, return_id=row.id)
    db.session.refresh(product)
    before = product.quantity
    with pytest.raises(ValidationError, match="No completed payment"):
        svc.complete_return(tenant_id=tenant.id, return_id=row.id, process_refund=True)
    db.session.refresh(product)
    assert product.quantity == before
    assert row.status == "approved"
    assert Refund.query.filter_by(tenant_id=tenant.id).count() == 0


def test_duplicate_return_quantity_is_rejected(app):
    tenant, _product, order, oi = _paid_order_without_payment(quantity=2)
    svc = RmaService()
    svc.create_return(
        tenant_id=tenant.id,
        order_id=order.id,
        items=[{"order_item_id": oi.id, "quantity": 2}],
    )
    with pytest.raises(ValidationError, match="Invalid return quantity"):
        svc.create_return(
            tenant_id=tenant.id,
            order_id=order.id,
            items=[{"order_item_id": oi.id, "quantity": 1}],
        )
    db.session.rollback()
    assert MerchandiseReturn.query.filter_by(tenant_id=tenant.id).count() == 1
    assert ReturnItem.query.filter_by(order_item_id=oi.id).count() == 1
    assert ReturnItem.query.filter_by(order_item_id=oi.id).one().quantity == 2
