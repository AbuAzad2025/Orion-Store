"""Manual (WhatsApp) orders: pending until the merchant confirms or cancels."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from catalog.product import Product

from core.exceptions import ValidationError
from orion.extensions import db
from order.order import Order, OrderItem
from tenant.tenant_config import TenantConfig

CHANNEL = "whatsapp"
PENDING_STATUS = "awaiting"
EXPIRE_DAYS = 14


def _commit_keep_loaded() -> None:
    session = db.session()
    previous = session.expire_on_commit
    session.expire_on_commit = False
    try:
        session.commit()
    finally:
        session.expire_on_commit = previous


class WhatsAppOrderService:
    def create(
        self,
        tenant,
        items: list[dict],
        customer_name: str = "",
        customer_email: str = "",
        notes: str = "",
    ) -> Order:
        """Create an unconfirmed order without touching stock or payments."""
        clean: list[dict] = []
        seen: dict[int, dict] = {}
        for row in items:
            product_id = int(row.get("product_id"))
            quantity = int(row.get("quantity") or 1)
            if quantity < 1:
                raise ValidationError("Quantity must be at least 1.")
            product = Product.query.filter_by(
                id=product_id, tenant_id=tenant.id, deleted_at=None
            ).first()
            if product is None or not product.is_published:
                raise ValidationError("Product not found.")
            total = Decimal(str(product.price)) * quantity
            entry = {
                "product": product,
                "product_id": product.id,
                "product_name": product.name,
                "product_sku": product.sku,
                "unit_price": product.price,
                "unit_cost": product.cost_price or Decimal("0"),
                "quantity": quantity,
                "total_price": total,
            }
            if product_id in seen:
                seen[product_id]["quantity"] += quantity
                seen[product_id]["total_price"] += total
            else:
                seen[product_id] = entry
                clean.append(entry)
        if not clean:
            raise ValidationError("No order items.")

        subtotal = sum((row["total_price"] for row in clean), Decimal("0"))
        config = TenantConfig.query.filter_by(tenant_id=tenant.id).first()
        if config and config.tax_included:
            from tax_svc.tax_service import TaxService

            tax_amount = TaxService().compute_tax_inclusive(tenant.id, subtotal, {})
            total = subtotal
        else:
            tax_amount = Decimal("0")
            total = subtotal + tax_amount
        number = f"WA-{tenant.id}-{uuid.uuid4().hex[:8].upper()}"
        order = Order(
            tenant_id=tenant.id,
            order_number=number,
            status=PENDING_STATUS,
            payment_status="pending",
            fulfillment_status="unfulfilled",
            customer_email=(
                customer_email or f"{number.lower()}@whatsapp.pending"
            ).lower(),
            customer_first_name=(customer_name or None),
            is_guest=True,
            shipping_address={"notes": notes, "channel": CHANNEL},
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=Decimal("0"),
            discount_amount=Decimal("0"),
            total=total,
            shipping_method_code=CHANNEL,
        )
        db.session.add(order)
        db.session.flush()
        for row in clean:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    tenant_id=tenant.id,
                    product_id=row["product_id"],
                    product_name=row["product_name"],
                    product_sku=row["product_sku"],
                    unit_price=row["unit_price"],
                    unit_cost=row["unit_cost"],
                    quantity=row["quantity"],
                    total_price=row["total_price"],
                )
            )
        _commit_keep_loaded()
        return order

    def _get(self, tenant_id: int, public_id: str) -> Order:
        order = Order.query.filter_by(public_id=public_id, tenant_id=tenant_id).first()
        if order is None or order.shipping_method_code != CHANNEL:
            raise ValidationError("Order not found.")
        return order

    def confirm(self, tenant_id: int, public_id: str) -> Order:
        order = self._get(tenant_id, public_id)
        if order.status != PENDING_STATUS:
            raise ValidationError("Order is no longer pending.")
        for item in db.session.query(OrderItem).filter_by(order_id=order.id).all():
            if item.product_id:
                db.session.query(Product).filter_by(
                    id=item.product_id, tenant_id=tenant_id
                ).update(
                    {Product.quantity: Product.quantity - item.quantity},
                    synchronize_session=False,
                )
        order.status = "confirmed"
        order.payment_status = "paid"
        order.fulfillment_status = "unfulfilled"
        _commit_keep_loaded()
        return order

    def cancel(self, tenant_id: int, public_id: str) -> Order:
        order = self._get(tenant_id, public_id)
        if order.status not in (PENDING_STATUS, "confirmed"):
            raise ValidationError("Order cannot be cancelled.")
        order.status = "cancelled"
        order.payment_status = "cancelled"
        _commit_keep_loaded()
        return order

    def expire_stale(self) -> int:
        """Auto-cancel WhatsApp orders left undecided for over two weeks."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=EXPIRE_DAYS)
        rows = Order.query.filter(
            Order.shipping_method_code == CHANNEL,
            Order.status == PENDING_STATUS,
            Order.created_at < cutoff,
        ).all()
        for order in rows:
            order.status = "cancelled"
            order.payment_status = "cancelled"
        if rows:
            _commit_keep_loaded()
        return len(rows)
