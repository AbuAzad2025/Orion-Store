"""Verified payment webhooks must produce real, idempotent financial effects."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone

import pytest

from order.order import Order
from orion.extensions import db
from payment.payment import Payment
from platform_models.financial_event import FinancialEvent
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_svc.tenant_service import TenantService

WEBHOOK_SECRET = "whsec_effects_test"


@pytest.fixture
def pending_order(app):
    """A tenant with an unpaid order and one pending provider payment."""
    with app.app_context():
        PlatformSettingsService().ensure_seeded()
        app.config["WEBHOOK_SECRET"] = WEBHOOK_SECRET
        suffix = uuid.uuid4().hex[:10]
        tenant = TenantService().create_tenant(
            name="Webhook Effects",
            slug=f"wh-effects-{suffix}",
            email=f"wh-effects-{suffix}@test.com",
        )
        order = Order(
            tenant_id=tenant.id,
            order_number=f"ORD-EFF-{suffix}",
            customer_email="buyer@effects.test",
            shipping_address={},
            subtotal="42.00",
            total="42.00",
            status="pending",
            payment_status="pending",
        )
        db.session.add(order)
        db.session.flush()
        payment = Payment(
            tenant_id=tenant.id,
            order_id=order.id,
            amount=order.total,
            currency="ILS",
            payment_method="stripe",
            payment_provider="stripe",
            status="pending",
        )
        db.session.add(payment)
        db.session.commit()
        return {
            "tenant_id": tenant.id,
            "order_id": order.id,
            "order_public_id": str(order.public_id),
            "payment_id": payment.id,
            "payment_public_id": str(payment.public_id),
        }


def _event_id(*prefix: str) -> str:
    return f"{'-'.join(prefix)}_{uuid.uuid4().hex}"


def _stripe_headers(raw: bytes, *, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    ts = int(time.time())
    to_sign = f"{ts}.{raw.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={ts},v1={sig}"}


def _post_stripe(
    client,
    tenant_id: int,
    payload: dict,
    *,
    secret: str = WEBHOOK_SECRET,
):
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return client.post(
        f"/webhooks/stripe/{tenant_id}",
        data=raw,
        content_type="application/json",
        headers=_stripe_headers(raw, secret=secret),
    )


def _paypal_headers(raw: bytes, *, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    signed = "|".join(["txn-1", ts, "wh-1", raw.decode("utf-8")]).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return {
        "Paypal-Auth-Algo": "HMAC-SHA256",
        "Paypal-Cert-Url": "https://api.paypal.com/certs",
        "Paypal-Transmit-Id": "txn-1",
        "Paypal-Transmit-Time": ts,
        "Paypal-Webhook-Id": "wh-1",
        "Paypal-Transmit-Sig": sig,
    }


def _state(app, ctx: dict) -> dict:
    """Plain-value snapshot (no detached ORM objects)."""
    with app.app_context():
        order = db.session.get(Order, ctx["order_id"])
        payment = db.session.get(Payment, ctx["payment_id"])
        events = (
            FinancialEvent.query.filter_by(tenant_id=ctx["tenant_id"])
            .order_by(FinancialEvent.id)
            .all()
        )
        return {
            "order_status": order.status,
            "order_payment_status": order.payment_status,
            "order_version": order.version,
            "payment_status": payment.status,
            "provider_payment_id": payment.provider_payment_id,
            "events": [
                (e.id, e.direction, e.event_type, str(e.amount)) for e in events
            ],
        }


def _success_payload(ctx: dict) -> dict:
    return {
        "id": _event_id("evt", "pi"),
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": _event_id("pi"),
                "metadata": {"order_public_id": ctx["order_public_id"]},
            }
        },
    }


def test_signed_webhook_updates_order_and_creates_financial_event(
    client, app, pending_order
):
    before = _state(app, pending_order)
    assert before["payment_status"] == "pending"
    assert before["order_payment_status"] == "pending"

    response = _post_stripe(
        client, pending_order["tenant_id"], _success_payload(pending_order)
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["received"] is True
    assert body["effect"]["processed"] is True
    assert body["effect"]["order_marked_paid"] is True

    after = _state(app, pending_order)
    assert after["payment_status"] == "completed"
    assert after["order_payment_status"] == "paid"
    assert after["order_status"] == "paid"
    assert len(after["events"]) == len(before["events"]) + 1
    assert any(
        e[1] == "inbound" and e[2] == "stripe.payment_succeeded"
        for e in after["events"]
    )


def test_duplicate_webhook_does_not_repeat_effect(client, app, pending_order):
    payload = _success_payload(pending_order)

    first = _post_stripe(client, pending_order["tenant_id"], payload)
    assert first.get_json()["effect"]["processed"] is True
    after_first = _state(app, pending_order)

    second = _post_stripe(client, pending_order["tenant_id"], payload)
    assert second.status_code == 200
    after_second = _state(app, pending_order)

    assert after_second["payment_status"] == "completed"
    assert after_second["order_payment_status"] == "paid"
    assert after_second["order_version"] == after_first["order_version"]
    assert after_second["events"] == after_first["events"]


def test_forged_webhook_is_rejected_without_effect(client, app, pending_order):
    before = _state(app, pending_order)

    response = _post_stripe(
        client,
        pending_order["tenant_id"],
        _success_payload(pending_order),
        secret="whsec_wrong_secret",
    )

    assert response.status_code == 400
    assert "Invalid signature" in response.get_json()["error"]
    assert _state(app, pending_order) == before


def test_paypal_capture_webhook_updates_order(client, app, pending_order):
    raw = json.dumps(
        {
            "id": _event_id("evt", "pp"),
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": _event_id("capture"),
                "custom_id": pending_order["order_public_id"],
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")
    response = client.post(
        f"/webhooks/paypal/{pending_order['tenant_id']}",
        data=raw,
        content_type="application/json",
        headers=_paypal_headers(raw),
    )

    assert response.status_code == 200
    assert response.get_json()["effect"]["processed"] is True
    after = _state(app, pending_order)
    assert after["payment_status"] == "completed"
    assert after["order_payment_status"] == "paid"
    assert any(e[2] == "paypal.capture_completed" for e in after["events"])


def test_bnpl_capture_webhook_updates_order(client, app, pending_order):
    raw = json.dumps(
        {
            "id": _event_id("evt", "bnpl"),
            "status": "captured",
            "order_public_id": pending_order["order_public_id"],
            "external_id": _event_id("txn"),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"), raw, hashlib.sha256
    ).hexdigest()
    response = client.post(
        f"/webhooks/bnpl/tabby/{pending_order['tenant_id']}",
        data=raw,
        content_type="application/json",
        headers={"X-Webhook-Signature": signature},
    )

    assert response.status_code == 200
    assert response.get_json()["effect"]["processed"] is True
    after = _state(app, pending_order)
    assert after["payment_status"] == "completed"
    assert after["order_payment_status"] == "paid"
    assert any(e[2] == "tabby.captured" for e in after["events"])


def test_refund_webhook_reverses_payment(client, app, pending_order):
    capture = _post_stripe(
        client, pending_order["tenant_id"], _success_payload(pending_order)
    )
    assert capture.get_json()["effect"]["processed"] is True

    refund_payload = {
        "id": _event_id("evt", "refund"),
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": _event_id("ch"),
                "metadata": {"payment_public_id": pending_order["payment_public_id"]},
            }
        },
    }
    response = _post_stripe(client, pending_order["tenant_id"], refund_payload)

    assert response.status_code == 200
    assert response.get_json()["effect"]["processed"] is True
    after = _state(app, pending_order)
    assert after["payment_status"] == "refunded"
    assert after["order_payment_status"] == "refunded"
    assert any(e[1] == "outbound" and e[2] == "payment.refund" for e in after["events"])
