"""Checkout — cart to order without payment (wave 3 #29)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from core.exceptions import ValidationError
from core.utils import utc_now
from order.cart import Cart
from order.order import Order, OrderEvent, OrderItem
from order_svc.cart_service import CartService
from orion.extensions import db


class CheckoutService:
    def __init__(self) -> None:
        self._carts = CartService()

    def checkout(
        self,
        *,
        cart: Cart,
        customer_email: str,
        shipping_address: dict,
        idempotency_key: str | None = None,
    ) -> Order:
        if not self._carts.list_items(cart):
            raise ValidationError("Cart is empty.")
        if idempotency_key:
            existing = Order.query.filter_by(
                tenant_id=cart.tenant_id, idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing

        subtotal = self._carts.cart_subtotal(cart)
        order = Order(
            tenant_id=cart.tenant_id,
            order_number=f"ORD-{cart.tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            customer_email=customer_email.strip().lower(),
            shipping_address=shipping_address,
            subtotal=subtotal,
            total=subtotal,
            status="pending",
            payment_status="pending",
            idempotency_key=idempotency_key,
        )
        db.session.add(order)
        db.session.flush()

        for item in self._carts.list_items(cart):
            from catalog.product import Product

            prod = Product.query.filter_by(
                id=item.product_id, tenant_id=cart.tenant_id
            ).first()
            if not prod or prod.quantity < item.quantity:
                db.session.rollback()
                name = prod.name if prod else "product"
                raise ValidationError(f"Insufficient stock for {name}.")
            prod.quantity -= item.quantity
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    tenant_id=cart.tenant_id,
                    product_id=item.product_id,
                    product_name=prod.name,
                    product_sku=prod.sku,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    total_price=item.total_price,
                )
            )

        cart.status = "converted"
        cart.converted_at = utc_now()
        db.session.add(
            OrderEvent(
                order_id=order.id,
                tenant_id=cart.tenant_id,
                event_type="order.created",
                message="Order created from cart checkout.",
            )
        )
        db.session.commit()
        return order
