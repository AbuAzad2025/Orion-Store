"""Domain event subscribers (wave 4 #49, §3.8)."""

from __future__ import annotations

from core.events import subscribe
from order.order import Order
from orion.extensions import db


def register_domain_event_handlers() -> None:
    subscribe("order.paid", _on_order_paid)
    subscribe("payment.refunded", _on_payment_refunded)


def _on_order_paid(order_id: int, tenant_id: int, **_: object) -> None:
    order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
    if not order:
        return
    if order.fulfillment_status == "unfulfilled":
        order.fulfillment_status = "paid_unfulfilled"
        db.session.commit()


def _on_payment_refunded(
    order_id: int | None = None, tenant_id: int | None = None, **_: object
) -> None:
    if not order_id or not tenant_id:
        return
    order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
    if not order:
        return
    order.payment_status = "refunded"
    db.session.commit()
