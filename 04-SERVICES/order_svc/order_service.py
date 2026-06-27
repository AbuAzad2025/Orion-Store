"""Order queries (wave 3 #30)."""

from __future__ import annotations

import uuid

from core.exceptions import NotFoundError
from order.order import Order


class OrderService:
    def get_by_public_id(self, tenant_id: int, public_id: str) -> Order:
        try:
            pid = uuid.UUID(public_id)
        except ValueError as exc:
            raise NotFoundError("Order not found.") from exc
        order = Order.query.filter_by(public_id=pid, tenant_id=tenant_id).first()
        if not order:
            raise NotFoundError("Order not found.")
        return order

    def mark_paid(self, order: Order) -> Order:
        order.payment_status = "paid"
        order.status = "paid"
        order.version += 1
        from orion.extensions import db

        db.session.commit()
        return order

    def list_for_tenant(self, tenant_id: int) -> list[Order]:
        return (
            Order.query.filter_by(tenant_id=tenant_id)
            .order_by(Order.created_at.desc())
            .all()
        )
