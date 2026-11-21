"""Production payment boundary — no fake success, real HTTP with idempotency."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
import requests

from core.crypto import CryptoService
from integrations.payments._http import idempotency_key as build_idempotency_key
from integrations.payments.stripe_connect import charge_stripe
from order.order import Order
from platform_models.tenant_gateway import TenantPaymentGateway


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _order(order_id: int = 501) -> Order:
    order = Order(
        tenant_id=1,
        order_number=f"ORD-LIVE-{order_id}",
        customer_email="buyer@test.com",
        shipping_address={},
        subtotal="10",
        total="10",
    )
    order.id = order_id
    return order


def _gateway(app, *, with_credentials: bool) -> TenantPaymentGateway:
    credentials = ""
    if with_credentials:
        encrypted = CryptoService(app.config["ENCRYPTION_KEY"]).encrypt(
            json.dumps({"secret_key": "sk_live_test"})
        )
        credentials = encrypted
    return TenantPaymentGateway(
        tenant_id=1,
        provider="stripe",
        display_name="Stripe",
        is_enabled=True,
        is_sandbox=False,
        credentials_encrypted=credentials,
        status="active",
    )


@pytest.fixture
def production_payments(app):
    previous = (
        app.config.get("PAYMENT_STUB_ALLOWED"),
        app.config.get("PAYMENT_LIVE_CALLS_ENABLED"),
    )
    app.config["PAYMENT_STUB_ALLOWED"] = False
    app.config["PAYMENT_LIVE_CALLS_ENABLED"] = True
    yield app
    (
        app.config["PAYMENT_STUB_ALLOWED"],
        app.config["PAYMENT_LIVE_CALLS_ENABLED"],
    ) = previous


def test_production_rejects_charge_without_credentials(app, production_payments):
    result = charge_stripe(
        order=_order(),
        gateway=_gateway(app, with_credentials=False),
        amount=Decimal("10.00"),
    )
    assert result == {"success": False, "error": "stripe_credentials_missing"}


def test_live_charge_sends_idempotency_key_and_returns_provider_id(
    app, production_payments, monkeypatch
):
    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return _FakeResponse({"id": "pi_real_123"})

    monkeypatch.setattr(requests, "post", fake_post)
    order = _order()

    result = charge_stripe(
        order=order,
        gateway=_gateway(app, with_credentials=True),
        amount=Decimal("10.00"),
    )

    assert result["success"] is True
    assert result["provider_payment_id"] == "pi_real_123"
    assert len(calls) == 1
    assert calls[0]["headers"]["Idempotency-Key"] == build_idempotency_key(order)
    assert calls[0]["headers"]["Authorization"] == "Bearer sk_live_test"


def test_provider_network_failure_is_structured(app, production_payments, monkeypatch):
    def failing_post(url, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "post", failing_post)
    result = charge_stripe(
        order=_order(),
        gateway=_gateway(app, with_credentials=True),
        amount=Decimal("10.00"),
    )
    assert result["success"] is False
    assert result["error"].startswith("provider_unreachable")
