"""Round-7/8 regression: bundles consume constituent stock at sale time."""

from __future__ import annotations

from decimal import Decimal

import pytest

from bundle.bundle import BundleItem, ProductBundle

from catalog_svc.product_service import ProductService
from core.exceptions import ValidationError
from order.order import OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from order_svc.whatsapp_order_service import WhatsAppOrderService
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


def _bundle_with_stock(*, quantity=10):
    tenant = TenantService().create_tenant(
        name="Bundle Store", slug="bundle-store", email="bundle@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Component",
        slug="component",
        price="10.00",
        quantity=quantity,
        is_published=True,
    )
    bundle = ProductBundle(
        tenant_id=tenant.id,
        name="Combo",
        slug="combo",
        bundle_price=Decimal("12.00"),
        is_published=True,
    )
    db.session.add(bundle)
    db.session.commit()
    db.session.add(
        BundleItem(
            tenant_id=tenant.id,
            bundle_id=bundle.id,
            product_id=product.id,
            quantity=2,
            discount_percent=Decimal("0"),
        )
    )
    db.session.commit()
    return tenant, product, bundle


def test_checkout_decrements_bundle_components(app):
    tenant, product, bundle = _bundle_with_stock()
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_bundle(cart=cart, bundle_id=bundle.id, quantity=2)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
    )
    db.session.refresh(product)
    assert product.quantity == 6
    item = OrderItem.query.filter_by(order_id=order.id).one()
    assert item.product_id is None
    assert Decimal(str(item.unit_price)) == Decimal("12.00")


def test_checkout_rejects_short_bundle_stock(app):
    tenant, product, bundle = _bundle_with_stock(quantity=3)
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_bundle(cart=cart, bundle_id=bundle.id, quantity=1)
    product.quantity = 1
    db.session.commit()
    with pytest.raises(ValidationError, match="Insufficient stock for bundle"):
        CheckoutService().checkout(
            cart=cart,
            customer_email="buyer@test.com",
            shipping_address={"city": "Ramallah"},
        )
    db.session.refresh(product)
    assert product.quantity == 1


def test_whatsapp_confirm_decrements_bundle_components(app):
    tenant, product, bundle = _bundle_with_stock()
    svc = WhatsAppOrderService()
    order = svc.create(
        tenant,
        items=[{"bundle_id": bundle.id, "quantity": 2}],
        customer_name="Buyer",
        customer_email="buyer@test.com",
    )
    db.session.refresh(product)
    assert product.quantity == 10
    confirmed = svc.confirm(tenant_id=tenant.id, public_id=order.public_id)
    db.session.refresh(product)
    assert confirmed.status == "confirmed"
    assert confirmed.payment_status == "paid"
    assert product.quantity == 6
    assert OrderItem.query.filter_by(order_id=order.id).one().product_sku == (
        f"bundle:{bundle.id}"
    )


def test_whatsapp_confirm_fails_closed_on_short_bundle_stock(app):
    tenant, product, bundle = _bundle_with_stock(quantity=3)
    svc = WhatsAppOrderService()
    order = svc.create(
        tenant,
        items=[{"bundle_id": bundle.id, "quantity": 1}],
        customer_email="buyer@test.com",
    )
    product.quantity = 1
    db.session.commit()
    with pytest.raises(ValidationError, match="Insufficient stock to confirm"):
        svc.confirm(tenant_id=tenant.id, public_id=order.public_id)
    db.session.refresh(product)
    db.session.refresh(order)
    assert product.quantity == 1
    assert order.status == "awaiting"
