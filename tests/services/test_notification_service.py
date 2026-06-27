"""Notification service tests (MVP stub)."""

from __future__ import annotations

from notification_svc.notification_service import NotificationService


def test_enqueue_payload():
    svc = NotificationService()
    row = svc.enqueue(
        tenant_id=1,
        channel="email",
        template="test",
        recipient="a@b.com",
        context={"x": 1},
    )
    assert row["tenant_id"] == 1
    assert row["channel"] == "email"
    assert row["status"] == "queued"
    assert row["context"]["x"] == 1


def test_send_order_confirmation(app):
    from order.order import Order

    order = Order(
        tenant_id=2,
        customer_email="buyer@test.com",
        order_number="ORD-1",
        total="99.00",
    )
    row = NotificationService().send_order_confirmation(order)
    assert row["template"] == "order_confirmation"
    assert row["recipient"] == "buyer@test.com"
    assert row["context"]["order_number"] == "ORD-1"
