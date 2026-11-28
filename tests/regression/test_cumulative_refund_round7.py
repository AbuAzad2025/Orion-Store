"""Round-7 regression: cumulative partial refunds close payment and order."""

from __future__ import annotations

from decimal import Decimal

import pytest

from catalog_svc.product_service import ProductService

from core.exceptions import ValidationError
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


def test_cumulative_partial_refunds_close_order(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Cumulative Refund", slug="cumulative-refund", email="refund@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Refundable",
        slug="refundable",
        price="10.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    payment = Payment.query.filter_by(order_id=order.id).one()
    total = Decimal(str(payment.amount))
    first = (total * Decimal("0.30")).quantize(Decimal("0.01"))
    svc = PaymentService()

    svc.refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
        amount=first,
        reason="first partial",
    )
    db.session.refresh(payment)
    db.session.refresh(order)
    assert payment.status == "completed"
    assert order.payment_status == "paid"
    assert Refund.query.filter_by(payment_id=payment.id).count() == 1

    svc.refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
        amount=total - first,
        reason="final partial",
    )
    db.session.refresh(payment)
    db.session.refresh(order)
    assert payment.status == "refunded"
    assert order.payment_status == "refunded"
    assert Refund.query.filter_by(payment_id=payment.id).count() == 2

    with pytest.raises(ValidationError, match="Only completed payments"):
        svc.refund(
            tenant_id=tenant.id,
            payment_public_id=str(payment.public_id),
            amount=Decimal("0.01"),
        )
