"""Workflow engine — event-triggered runs, idempotency and tenant scoping."""

from __future__ import annotations

from unittest.mock import patch

from support.http import auth_headers
from workflow.workflow import WorkflowRun
from workflow_svc.workflow_service import WorkflowService

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from core.events import publish
from order.order import Order, OrderEvent
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from payment_svc.payment_service import PaymentService
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService

EMAIL_TARGET = (
    "notification_svc.notification_service.NotificationService.send_action_email"
)


def _tenant(name: str, slug: str, email: str):
    return TenantService().create_tenant(name=name, slug=slug, email=email)


def _order_row(tenant, *, order_number: str, email: str) -> Order:
    order = Order(
        tenant_id=tenant.id,
        customer_email=email,
        order_number=order_number,
        total="10.00",
        payment_status="paid",
        fulfillment_status="unfulfilled",
        shipping_address={},
    )
    db.session.add(order)
    db.session.commit()
    return order


def _checkout_order(tenant):
    PlatformSettingsService().ensure_seeded()
    product = ProductService().create(
        tenant_id=tenant.id,
        name="WF Item",
        slug="wf-item",
        price="10.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    return CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@wf.com",
        shipping_address={"city": "Ramallah"},
    )


def test_order_paid_runs_workflow_to_completion(app):
    tenant = _tenant("WF Paid", "wf-paid", "wf-paid@test.com")
    order = _checkout_order(tenant)
    wf = WorkflowService().create_definition(
        tenant_id=tenant.id,
        name="Paid Receipt",
        trigger_event="order.paid",
        actions=[{"type": "send_email", "template": "workflow_receipt"}],
    )
    GatewayService().ensure_cod_gateway(tenant.id)

    with patch(EMAIL_TARGET) as send_email:
        PaymentService().pay_order(
            tenant_id=tenant.id,
            order_public_id=str(order.public_id),
            payment_method="cod",
        )
        send_email.assert_called_once()

    runs = WorkflowRun.query.filter_by(tenant_id=tenant.id, definition_id=wf.id).all()
    assert len(runs) == 1
    run = runs[0]
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.trigger_event_id == order.id

    kwargs = send_email.call_args.kwargs
    assert kwargs["tenant_id"] == tenant.id
    assert kwargs["recipient"] == "buyer@wf.com"
    assert kwargs["template"] == "workflow_receipt"


def test_duplicate_event_does_not_run_workflow_twice(app):
    tenant = _tenant("WF Dup", "wf-dup", "wf-dup@test.com")
    order = _order_row(tenant, order_number="ORD-WF-DUP", email="dup@wf.com")
    wf = WorkflowService().create_definition(
        tenant_id=tenant.id,
        name="Dup Receipt",
        trigger_event="order.paid",
        actions=[{"type": "send_email", "template": "dup_receipt"}],
    )

    with patch(EMAIL_TARGET) as send_email:
        publish("order.paid", order_id=order.id, tenant_id=tenant.id)
        publish("order.paid", order_id=order.id, tenant_id=tenant.id)
        assert send_email.call_count == 1

    runs = WorkflowRun.query.filter_by(definition_id=wf.id).all()
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].trigger_event_id == order.id


def test_workflow_is_tenant_scoped(app):
    tenant_a = _tenant("WF A", "wf-a", "a@test.com")
    tenant_b = _tenant("WF B", "wf-b", "b@test.com")
    wf_a = WorkflowService().create_definition(
        tenant_id=tenant_a.id,
        name="A Paid",
        trigger_event="order.paid",
        actions=[{"type": "send_email", "template": "a_receipt"}],
    )

    with patch(EMAIL_TARGET):
        # Event for tenant B must not touch tenant A's definition.
        publish("order.paid", order_id=777, tenant_id=tenant_b.id)
        assert WorkflowRun.query.count() == 0
        publish("order.paid", order_id=888, tenant_id=tenant_a.id)

    runs = WorkflowRun.query.filter_by(tenant_id=tenant_a.id).all()
    assert len(runs) == 1
    assert runs[0].definition_id == wf_a.id
    assert runs[0].status == "completed"
    assert WorkflowRun.query.filter_by(tenant_id=tenant_b.id).count() == 0


def test_tag_order_action_records_tag(app):
    tenant = _tenant("WF Tag", "wf-tag", "wf-tag@test.com")
    order = _order_row(tenant, order_number="ORD-WF-TAG", email="tag@wf.com")
    wf = WorkflowService().create_definition(
        tenant_id=tenant.id,
        name="Tag VIP",
        trigger_event="order.paid",
        actions=[{"type": "tag_order", "tag": "vip"}],
    )

    runs = WorkflowService().trigger(
        "order.paid", tenant.id, {"order_id": order.id, "tenant_id": tenant.id}
    )

    assert len(runs) == 1
    assert runs[0].status == "completed"
    tags = OrderEvent.query.filter_by(
        order_id=order.id, tenant_id=tenant.id, event_type="workflow_tag"
    ).all()
    assert len(tags) == 1
    assert tags[0].message == "vip"


def test_manual_run_endpoint_is_admin_protected_and_executes(app, client):
    PlatformSettingsService().ensure_seeded()
    tenant = _tenant("WF API", "wf-api", "wf-api@test.com")
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@wf-api.com",
        password="password123",
        is_admin=True,
    )
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="cust@wf-api.com",
        password="password123",
        is_admin=False,
    )
    wf = WorkflowService().create_definition(
        tenant_id=tenant.id,
        name="Manual",
        trigger_event="order.created",
        actions=[{"type": "send_email", "template": "manual"}],
    )
    url = f"/api/v1/workflow/definitions/{wf.id}/run"
    admin_headers = auth_headers(admin, app=app, tenant_id=tenant.slug)
    customer_headers = auth_headers(customer, app=app, tenant_id=tenant.slug)

    assert (
        client.post(
            url, json={"customer_email": "x@wf.com"}, headers=customer_headers
        ).status_code
        == 403
    )
    assert client.post(url, json={}).status_code in (401, 403)

    with patch(EMAIL_TARGET) as send_email:
        resp = client.post(
            url,
            json={"customer_email": "manual@wf.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["run"]["status"] == "completed"
        send_email.assert_called_once()

    assert WorkflowRun.query.filter_by(definition_id=wf.id).count() == 1
