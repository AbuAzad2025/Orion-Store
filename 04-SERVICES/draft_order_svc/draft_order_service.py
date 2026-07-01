from __future__ import annotations

import uuid
from decimal import Decimal

from catalog.product import Product
from core.exceptions import NotFoundError, ValidationError
from draft_order.draft_order import DraftOrder, DraftOrderItem
from order.order import Order, OrderEvent, OrderItem
from orion.extensions import db


class DraftOrderService:
    def create_draft(
        self, *, tenant_id: int, customer_email: str | None = None, notes: str | None = None,
        shipping_address: dict | None = None, send_email_invite: bool = False,
    ) -> DraftOrder:
        draft = DraftOrder(
            tenant_id=tenant_id, draft_number=f"DRF-{tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            customer_email=customer_email, notes=notes, shipping_address=shipping_address or {},
            send_email_invite=send_email_invite,
        )
        db.session.add(draft)
        db.session.commit()
        return draft

    def add_item(self, *, tenant_id: int, draft_id: int, product_id: int, quantity: int) -> DraftOrderItem:
        draft = DraftOrder.query.filter_by(id=draft_id, tenant_id=tenant_id).first()
        if not draft:
            raise NotFoundError("Draft order not found.")
        if draft.status != "draft":
            raise ValidationError("Draft is no longer editable.")
        product = Product.query.filter_by(id=product_id, tenant_id=tenant_id, deleted_at=None).first()
        if not product:
            raise NotFoundError("Product not found.")
        unit = product.price
        total = unit * quantity
        item = DraftOrderItem(
            draft_order_id=draft.id, tenant_id=tenant_id, product_id=product_id,
            product_name=product.name, product_sku=product.sku,
            unit_price=unit, quantity=quantity, total_price=total,
        )
        db.session.add(item)
        db.session.flush()
        self._recalc(draft)
        db.session.commit()
        return item

    def convert_to_order(self, *, tenant_id: int, draft_id: int, customer_email: str) -> Order:
        draft = DraftOrder.query.filter_by(id=draft_id, tenant_id=tenant_id).first()
        if not draft:
            raise NotFoundError("Draft order not found.")
        if draft.status == "converted":
            raise ValidationError("Draft already converted.")
        items = DraftOrderItem.query.filter_by(draft_order_id=draft.id).all()
        if not items:
            raise ValidationError("Draft has no items.")
        order = Order(
            tenant_id=tenant_id, order_number=f"ORD-DRF-{uuid.uuid4().hex[:8].upper()}",
            customer_email=customer_email.strip().lower(), shipping_address=draft.shipping_address or {},
            subtotal=draft.subtotal, tax_amount=draft.tax_amount, shipping_cost=draft.shipping_cost,
            discount_amount=draft.discount_amount, total=draft.total, status="pending", payment_status="pending",
        )
        db.session.add(order)
        db.session.flush()
        for item in items:
            prod = Product.query.filter_by(id=item.product_id, tenant_id=tenant_id).first() if item.product_id else None
            db.session.add(OrderItem(
                order_id=order.id, tenant_id=tenant_id, product_id=item.product_id,
                product_name=item.product_name, product_sku=item.product_sku,
                unit_price=item.unit_price, quantity=item.quantity, total_price=item.total_price,
            ))
            if prod:
                prod.quantity -= item.quantity
        draft.status = "converted"
        draft.converted_order_id = order.id
        db.session.add(OrderEvent(order_id=order.id, tenant_id=tenant_id, event_type="order.created", message=f"Created from draft {draft.draft_number}"))
        db.session.commit()
        return order

    def list_drafts(self, tenant_id: int) -> list[DraftOrder]:
        return DraftOrder.query.filter_by(tenant_id=tenant_id).order_by(DraftOrder.created_at.desc()).all()

    def _recalc(self, draft: DraftOrder) -> None:
        items = DraftOrderItem.query.filter_by(draft_order_id=draft.id).all()
        draft.subtotal = sum((item.total_price for item in items), Decimal("0"))
        draft.total = draft.subtotal + draft.tax_amount + draft.shipping_cost - draft.discount_amount
