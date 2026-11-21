"""Changing a product price must never rewrite already-sold orders."""

from __future__ import annotations

from decimal import Decimal

from catalog_svc.product_service import ProductService
from order.order import OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


def _checkout(tenant, product, quantity):
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=quantity)
    return CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
    )


def test_price_change_does_not_affect_past_orders(app):
    tenant = TenantService().create_tenant(
        name="Price Store", slug="price-store", email="price@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Priced Item",
        slug="priced-item",
        price="10.00",
        quantity=20,
        is_published=True,
    )
    first_order = _checkout(tenant, product, 2)
    first_total = first_order.total
    with app.app_context():
        first_item = OrderItem.query.filter_by(order_id=first_order.id).first()
        first_unit_price = first_item.unit_price
        first_line_total = first_item.total_price

    ProductService().update(product, price=Decimal("99.00"))

    with app.app_context():
        db.session.expire_all()
        old_order = db.session.merge(first_order)
        old_item = OrderItem.query.filter_by(order_id=first_order.id).first()
        assert old_order.total == first_total
        assert old_item.unit_price == first_unit_price == Decimal("10.00")
        assert old_item.total_price == first_line_total

    second_order = _checkout(tenant, product, 1)
    with app.app_context():
        second_item = OrderItem.query.filter_by(order_id=second_order.id).first()
        assert second_item.unit_price == Decimal("99.00")
        assert second_order.total != first_total
