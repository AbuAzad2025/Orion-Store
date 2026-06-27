"""Domain event handler integration — notification on order.paid."""

from __future__ import annotations

from unittest.mock import patch

from core.events import publish
from order.order import Order
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


def test_order_paid_sends_confirmation(app):
    tenant = TenantService().create_tenant(
        name="Evt Store", slug="evt-store", email="evt@test.com"
    )
    order = Order(
        tenant_id=tenant.id,
        customer_email="paid@test.com",
        order_number="ORD-EVT-99",
        total="50.00",
        fulfillment_status="unfulfilled",
        payment_status="paid",
        shipping_address={},
    )
    db.session.add(order)
    db.session.commit()

    with patch(
        "notification_svc.notification_service.NotificationService.send_order_confirmation"
    ) as mock_send:
        publish("order.paid", order_id=order.id, tenant_id=order.tenant_id)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0].id == order.id

    db.session.refresh(order)
    assert order.fulfillment_status == "paid_unfulfilled"
