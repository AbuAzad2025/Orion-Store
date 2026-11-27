"""Manual (WhatsApp) orders: pending until the merchant confirms or cancels."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import update

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
            if quantity > (product.quantity or 0):
                raise ValidationError("Requested quantity is not available.")
            raw_price = row.get("unit_price")
            unit_price = (
                Decimal(str(raw_price))
                if raw_price is not None
                else Decimal(str(product.price))
            )
            total = unit_price * quantity
            entry = {
                "product": product,
                "product_id": product.id,
                "product_name": str(row.get("product_name") or product.name),
                "product_sku": product.sku,
                "unit_price": unit_price,
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
        from tax_svc.tax_service import TaxService

        address = {"notes": notes, "channel": CHANNEL}
        if config and config.tax_included:
            tax_amount = TaxService().compute_tax_inclusive(
                tenant.id, subtotal, address
            )
            total = subtotal
        else:
            tax_amount = TaxService().compute_tax(
                tenant.id, subtotal, address, Decimal("0")
            )
            total = subtotal + tax_amount
        number = f"WA-{tenant.id}-{uuid.uuid4().hex[:8].upper()}"
        order = Order(
            tenant_id=tenant.id,
            order_number=number,
            status=PENDING_STATUS,
            payment_status="pending",
            fulfillment_status="unfulfilled",
            customer_email=(
                str(customer_email or "").strip().lower()
                or f"{number.lower()}@whatsapp.pending"
            ),
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
        changed = db.session.execute(
            update(Order)
            .where(
                Order.id == order.id,
                Order.tenant_id == tenant_id,
                Order.status == PENDING_STATUS,
            )
            .values(
                status="confirmed",
                payment_status="paid",
                fulfillment_status="unfulfilled",
            )
        ).rowcount
        if changed != 1:
            raise ValidationError("Order is no longer pending.")
        for item in db.session.query(OrderItem).filter_by(order_id=order.id).all():
            if not item.product_id:
                continue
            reserved = db.session.execute(
                update(Product)
                .where(
                    Product.id == item.product_id,
                    Product.tenant_id == tenant_id,
                    Product.quantity >= item.quantity,
                )
                .values(quantity=Product.quantity - item.quantity)
            ).rowcount
            if reserved != 1:
                db.session.rollback()
                raise ValidationError("Insufficient stock to confirm this order.")
        self._record_payment_and_invoice(order)
        db.session.refresh(order)
        return order

    def _record_payment_and_invoice(self, order: Order) -> None:
        """Book the manual payment through the same pipeline as gateway payments."""
        from core.events import publish
        from payment.payment import Payment
        from platform_svc.commission_service import CommissionService
        from platform_svc.document_renderer import DocumentRenderer
        from platform_svc.financial_events_service import FinancialEventsService
        from tenant.tenant import Tenant

        tenant = db.session.get(Tenant, order.tenant_id)
        currency = (tenant.default_currency if tenant else None) or "ILS"
        payment = Payment(
            tenant_id=order.tenant_id,
            order_id=order.id,
            amount=order.total,
            currency=currency,
            payment_method="manual",
            payment_provider="whatsapp",
            status="completed",
            provider_payment_id=order.order_number,
        )
        db.session.add(payment)
        db.session.flush()
        event = FinancialEventsService().record_inbound(
            tenant_id=order.tenant_id,
            amount=order.total,
            event_type="order.payment.whatsapp",
            source_entity="payment",
            source_id=payment.id,
            currency=currency,
            description=f"Manual WhatsApp payment for {order.order_number}",
        )
        payment.financial_event_id = event.id
        CommissionService().apply_from_event(
            event, payment_id=payment.id, order_id=order.id
        )
        DocumentRenderer().generate_invoice(
            order=order, payment=payment, financial_event=event
        )
        publish("order.paid", order_id=order.id, tenant_id=order.tenant_id)

    def cancel(self, tenant_id: int, public_id: str) -> Order:
        order = self._get(tenant_id, public_id)
        if order.status != PENDING_STATUS:
            raise ValidationError("Only pending orders can be cancelled.")
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
