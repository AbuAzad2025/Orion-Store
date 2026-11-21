"""Checkout — cart to order without payment (wave 3 #29, wave 6 totals)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from discount_svc.voucher_service import VoucherService
from shipping_svc.shipping_service import ShippingService
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from store_credit_svc.store_credit_service import StoreCreditService
from tax_svc.tax_service import TaxService

from core.caching import invalidate_tenant_catalog
from core.exceptions import ValidationError
from core.utils import utc_now
from order.cart import Cart
from order.order import Order, OrderEvent, OrderItem
from order_svc.cart_service import CartService
from orion.extensions import db


class CheckoutService:
    def __init__(self) -> None:
        self._carts = CartService()
        self._shipping = ShippingService()
        self._vouchers = VoucherService()
        self._credits = StoreCreditService()

    def checkout(
        self,
        *,
        cart: Cart,
        customer_email: str,
        shipping_address: dict,
        user_id: int | None = None,
        is_guest: bool = True,
        idempotency_key: str | None = None,
        shipping_method_code: str | None = None,
        voucher_code: str | None = None,
        use_store_credit: bool = False,
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

        tax_amount = TaxService().compute_tax(
            tenant_id=cart.tenant_id,
            subtotal=subtotal,
            shipping_address=shipping_address,
            shipping_cost=shipping_cost,
        )
        total = subtotal - discount_amount + shipping_cost + tax_amount
        if total < Decimal("0"):
            total = Decimal("0")

        credit_amount = Decimal("0")
        credit_balance_after = None
        if use_store_credit:
            available = self._credits.get_balance(
                tenant_id=cart.tenant_id, customer_email=customer_email
            )
            credit_amount = min(available, total).quantize(Decimal("0.01"))
            if credit_amount > 0:
                total -= credit_amount
        if credit_amount <= 0:
            payment_status = "pending"
        elif total == Decimal("0"):
            payment_status = "paid"
        else:
            payment_status = "partially_paid"

        order = Order(
            tenant_id=cart.tenant_id,
            order_number=f"ORD-{cart.tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            customer_email=customer_email.strip().lower(),
            user_id=user_id,
            is_guest=is_guest,
            shipping_address=shipping_address,
            shipping_method_code=method_code,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            discount_amount=discount_amount,
            discount_code=discount_code,
            total=total,
            status="pending",
            payment_status=payment_status,
            idempotency_key=idempotency_key,
        )
        db.session.add(order)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            if idempotency_key:
                existing = Order.query.filter_by(
                    tenant_id=cart.tenant_id, idempotency_key=idempotency_key
                ).first()
                if existing:
                    return existing
            raise

        for item in self._carts.list_items(cart):
            from catalog.product import Product

            prod = Product.query.filter_by(
                id=item.product_id, tenant_id=cart.tenant_id
            ).first()
            if not prod:
                db.session.rollback()
                raise ValidationError("Insufficient stock for product.")
            result = db.session.execute(
                update(Product)
                .where(
                    Product.id == item.product_id,
                    Product.tenant_id == cart.tenant_id,
                    Product.quantity >= item.quantity,
                )
                .values(quantity=Product.quantity - item.quantity)
            )
            if result.rowcount != 1:
                db.session.rollback()
                raise ValidationError(f"Insufficient stock for {prod.name}.")
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

        if credit_amount > 0:
            credit = self._credits.deduct(
                tenant_id=cart.tenant_id,
                customer_email=customer_email,
                amount=credit_amount,
                reference_type="order",
                reference_id=order.id,
                commit=False,
            )
            credit_balance_after = credit.balance

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
        if credit_amount > 0:
            db.session.add(
                OrderEvent(
                    order_id=order.id,
                    tenant_id=cart.tenant_id,
                    event_type="order.store_credit_applied",
                    message=f"Applied {credit_amount} store credit.",
                    metadata_json={
                        "amount": str(credit_amount),
                        "balance_after": str(credit_balance_after),
                    },
                )
            )
        db.session.commit()
        # Publish the domain event so workflow and fraud subscribers (registered
        # in core.event_handlers) actually run in production — the OrderEvent row
        # above is an audit record, not an event-bus dispatch.
        from core.events import publish

        publish(
            "order.created",
            order_id=order.id,
            tenant_id=cart.tenant_id,
            customer_email=order.customer_email,
            total=str(order.total),
        )
        invalidate_tenant_catalog(cart.tenant_id)
        # Keep warehouse stock aligned with the saleable stock we just reduced.
        try:
            from oms_svc.oms_service import OmsService

            oms = OmsService()
            for item in self._carts.list_items(cart):
                oms.sync_product_to_warehouse(
                    tenant_id=cart.tenant_id, product_id=item.product_id
                )
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "warehouse sync after checkout failed: %s", exc
            )
        return order
