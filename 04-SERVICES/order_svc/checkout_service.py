"""Checkout — cart to order without payment (wave 3 #29, wave 6 totals)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from discount_svc.voucher_service import VoucherService
from shipping_svc.shipping_service import ShippingService

from core.exceptions import ValidationError
from core.utils import utc_now
from order.cart import Cart
from order.order import Order, OrderEvent, OrderItem
from order_svc.cart_service import CartService
from orion.extensions import db
from tenant.tenant_config import TenantConfig


class CheckoutService:
    def __init__(self) -> None:
        self._carts = CartService()
        self._shipping = ShippingService()
        self._vouchers = VoucherService()

    def checkout(
        self,
        *,
        cart: Cart,
        customer_email: str,
        shipping_address: dict,
        idempotency_key: str | None = None,
        shipping_method_code: str | None = None,
        voucher_code: str | None = None,
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
        discount_amount = Decimal("0")
        discount_code = None
        free_shipping = False

        if voucher_code:
            preview = self._vouchers.validate(cart.tenant_id, voucher_code, subtotal)
            discount_amount = preview.discount_amount
            discount_code = preview.voucher.code
            free_shipping = preview.is_free_shipping

        method_code = shipping_method_code
        if not method_code:
            default = (
                self._shipping.query_methods(cart.tenant_id)
                .filter_by(is_default=True)
                .first()
            )
            if default:
                method_code = default.code

        shipping_cost = Decimal("0")
        if method_code:
            shipping_cost = self._shipping.calculate_cost(
                tenant_id=cart.tenant_id,
                method_code=method_code,
                subtotal=subtotal,
                shipping_address=shipping_address,
                free_shipping=free_shipping,
            )

        tax_amount = self._compute_tax(cart.tenant_id, subtotal)
        total = subtotal - discount_amount + shipping_cost + tax_amount
        if total < Decimal("0"):
            total = Decimal("0")

        order = Order(
            tenant_id=cart.tenant_id,
            order_number=f"ORD-{cart.tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            customer_email=customer_email.strip().lower(),
            shipping_address=shipping_address,
            shipping_method_code=method_code,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            discount_amount=discount_amount,
            discount_code=discount_code,
            total=total,
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

        if voucher_code and discount_code:
            voucher = self._vouchers.get_by_code(cart.tenant_id, discount_code)
            self._vouchers.record_usage(voucher)

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

    def _compute_tax(self, tenant_id: int, subtotal: Decimal) -> Decimal:
        config = TenantConfig.query.filter_by(tenant_id=tenant_id).first()
        if not config or config.tax_included or config.tax_rate <= 0:
            return Decimal("0")
        return (subtotal * config.tax_rate).quantize(Decimal("0.01"))
