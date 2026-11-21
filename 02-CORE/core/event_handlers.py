"""Domain event subscribers (wave 4 #49, §3.8)."""

from __future__ import annotations

from core.events import subscribe
from order.order import Order
from orion.extensions import db


def register_domain_event_handlers() -> None:
    subscribe("order.paid", _on_order_paid)
    subscribe("payment.refunded", _on_payment_refunded)
    # Workflow subscribers run after the domain handlers above.
    subscribe("order.paid", _on_order_paid_workflow)
    subscribe("payment.refunded", _on_payment_refunded_workflow)
    subscribe("order.created", _on_order_created_workflow)
    __import__(
        "fraud_svc.fraud_service", fromlist=["install_order_created_subscriber"]
    ).install_order_created_subscriber()


def _on_order_paid(order_id: int, tenant_id: int, **_: object) -> None:
    order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
    if not order:
        return
    if order.fulfillment_status == "unfulfilled":
        order.fulfillment_status = "paid_unfulfilled"
        db.session.commit()
    from notification_svc.notification_service import NotificationService

    NotificationService().send_order_confirmation(order)


def _on_payment_refunded(
    order_id: int | None = None,
    tenant_id: int | None = None,
    refund_id: int | None = None,
    **_: object,
) -> None:
    if not tenant_id:
        return
    # A refund reverses the commission booked for the original payment.
    # payment_service publishes refund_id (not payment_id), so resolve the
    # payment from the refund row and delegate to the tenant-scoped API.
    if refund_id:
        from payment.refund import Refund
        from platform_svc.commission_service import CommissionService

        refund = Refund.query.filter_by(id=refund_id, tenant_id=tenant_id).first()
        if refund:
            CommissionService().reverse_for_payment(tenant_id, refund.payment_id)
    if not order_id:
        return
    order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
    if not order:
        return
    order.payment_status = "refunded"
    db.session.commit()


# ---------------------------------------------------------------------------
# Workflow automation subscribers (registered after the handlers above).
# ---------------------------------------------------------------------------


def _on_order_paid_workflow(**payload: object) -> None:
    _trigger_workflow("order.paid", payload)


def _on_payment_refunded_workflow(**payload: object) -> None:
    _trigger_workflow("payment.refunded", payload)


def _on_order_created_workflow(**payload: object) -> None:
    _trigger_workflow("order.created", payload)


def _trigger_workflow(event_name: str, payload: dict) -> None:
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        return
    from workflow_svc.workflow_service import WorkflowService

    WorkflowService().trigger(
        event_type=event_name,
        tenant_id=tenant_id,
        payload=payload,
    )
