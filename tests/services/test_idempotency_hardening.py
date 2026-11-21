"""Hardening: no duplicate charges, no duplicate orders, no refund commission."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError
from order_svc.checkout_service import CheckoutService
from payment.payment import Payment
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from platform_models.financial_event import FinancialEvent
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService
from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService


def _order(app, tenant, product, idempotency_key=None):
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    return CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
        idempotency_key=idempotency_key,
    )


def test_duplicate_payment_is_rejected(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Idem Store", slug="idem-store", email="idem@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Idem Item",
        slug="idem-item",
        price="10.00",
        quantity=5,
        is_published=True,
    )
    order = _order(app, tenant, product)
    GatewayService().ensure_cod_gateway(tenant.id)
    with app.app_context():
        PaymentService().pay_order(
            tenant_id=tenant.id,
            order_public_id=str(order.public_id),
            payment_method="cod",
        )
        assert Payment.query.filter_by(order_id=order.id).count() == 1
        with pytest.raises(ValidationError, match="already paid"):
            PaymentService().pay_order(
                tenant_id=tenant.id,
                order_public_id=str(order.public_id),
                payment_method="cod",
            )
        assert Payment.query.filter_by(order_id=order.id).count() == 1


def test_duplicate_checkout_idempotency_key_returns_same_order(app):
    tenant = TenantService().create_tenant(
        name="Idem Store 2", slug="idem-store-2", email="idem2@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Idem Item 2",
        slug="idem-item-2",
        price="10.00",
        quantity=5,
        is_published=True,
    )
    first = _order(app, tenant, product, idempotency_key="checkout-key-1")
    second = _order(app, tenant, product, idempotency_key="checkout-key-1")
    assert first.id == second.id
    with app.app_context():
        from order.order import Order

        assert Order.query.filter_by(tenant_id=tenant.id).count() == 1


def test_refund_creates_negative_event_without_commission(app):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Refund Store", slug="refund-store", email="refund@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Refund Item",
        slug="refund-item",
        price="10.00",
        quantity=5,
        is_published=True,
    )
    order = _order(app, tenant, product)
    GatewayService().ensure_cod_gateway(tenant.id)
    with app.app_context():
        result = PaymentService().pay_order(
            tenant_id=tenant.id,
            order_public_id=str(order.public_id),
            payment_method="cod",
        )
        payment = Payment.query.filter_by(order_id=order.id).first()
        refund = PaymentService().refund(
            tenant_id=tenant.id, payment_public_id=str(payment.public_id)
        )
        event = FinancialEvent.query.filter_by(event_type="payment.refund").first()
        assert event is not None
        assert event.amount < 0
        assert event.commission_amount is None
        assert refund["commission_ledger_id"] is None
