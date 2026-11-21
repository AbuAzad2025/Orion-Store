"""Actual provider refunds: partial/full amounts, dedupe, and live HTTP payloads."""

from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
import requests

from catalog_svc.product_service import ProductService
from core.crypto import CryptoService
from core.exceptions import ConflictError, ValidationError
from integrations.payments.bnpl import refund_payment as refund_bnpl
from integrations.payments.palpay import refund_payment as refund_palpay
from integrations.payments.paypal import refund_payment as refund_paypal
from integrations.payments.stripe_connect import refund_payment as refund_stripe
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from payment_svc.payment_service import PaymentService
from platform_models.financial_event import FinancialEvent
from platform_models.tenant_gateway import TenantPaymentGateway
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _paid_payment(
    app, *, provider: str = "cod", provider_payment_id: str | None = None
):
    """Drive a real checkout + COD charge, then point the payment at a provider."""
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name="Refund Provider Store",
        slug="refund-provider-store",
        email="refund-provider@test.com",
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Refund Item",
        slug="refund-item",
        price="10.00",
        quantity=5,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@test.com",
        shipping_address={"city": "Ramallah"},
    )
    GatewayService().ensure_cod_gateway(tenant.id)
    PaymentService().pay_order(
        tenant_id=tenant.id,
        order_public_id=str(order.public_id),
        payment_method="cod",
    )
    payment = Payment.query.filter_by(order_id=order.id).first()
    payment.payment_provider = provider
    payment.provider_payment_id = provider_payment_id or f"test_{payment.id}"
    db.session.commit()
    return tenant, payment


def _attach_stripe_gateway(app, tenant_id: int) -> None:
    encrypted = CryptoService(app.config["ENCRYPTION_KEY"]).encrypt(
        json.dumps({"secret_key": "sk_live_test"})
    )
    db.session.add(
        TenantPaymentGateway(
            tenant_id=tenant_id,
            provider="stripe",
            display_name="Stripe",
            is_enabled=True,
            is_sandbox=False,
            credentials_encrypted=encrypted,
            status="active",
        )
    )
    db.session.commit()


def test_partial_refund_records_amount_and_provider_id(app):
    tenant, payment = _paid_payment(app, provider="stripe")

    result = PaymentService().refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
        amount=Decimal("4.00"),
        reason="partial return",
    )

    refund = Refund.query.filter_by(payment_id=payment.id).one()
    assert refund.amount == Decimal("4.00")
    assert refund.provider_refund_id
    assert refund.status == "completed"
    assert payment.status == "completed"  # partial refund keeps the payment open
    assert result["provider_refund_id"] == refund.provider_refund_id
    assert result["refund"]["provider_refund_id"] == refund.provider_refund_id
    assert result["uncertain"] is False
    event = FinancialEvent.query.filter_by(event_type="payment.refund").one()
    assert event.amount == Decimal("-4.00")


def test_full_refund_defaults_to_full_amount(app):
    tenant, payment = _paid_payment(app)

    result = PaymentService().refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
    )

    refund = Refund.query.filter_by(payment_id=payment.id).one()
    assert refund.amount == payment.amount == Decimal("10.00")
    assert payment.status == "refunded"
    assert result["refund"]["amount"] == "10.00"
    assert refund.provider_refund_id


def test_duplicate_refund_is_rejected(app):
    tenant, payment = _paid_payment(app)
    svc = PaymentService()

    svc.refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
        amount=Decimal("3.00"),
    )
    with pytest.raises(ConflictError, match="already refunded"):
        svc.refund(
            tenant_id=tenant.id,
            payment_public_id=str(payment.public_id),
            amount=Decimal("3.00"),
        )
    assert Refund.query.filter_by(payment_id=payment.id).count() == 1


def test_refund_amount_bounds_are_validated(app):
    tenant, payment = _paid_payment(app)
    svc = PaymentService()

    with pytest.raises(ValidationError):
        svc.refund(
            tenant_id=tenant.id,
            payment_public_id=str(payment.public_id),
            amount=Decimal("10.01"),
        )
    with pytest.raises(ValidationError):
        svc.refund(
            tenant_id=tenant.id,
            payment_public_id=str(payment.public_id),
            amount=Decimal("0"),
        )
    assert Refund.query.filter_by(payment_id=payment.id).count() == 0


def test_live_refund_sends_exact_amount_to_provider(app, monkeypatch):
    previous = app.config.get("PAYMENT_LIVE_CALLS_ENABLED")
    app.config["PAYMENT_LIVE_CALLS_ENABLED"] = True
    try:
        tenant, payment = _paid_payment(
            app, provider="stripe", provider_payment_id="pi_abc"
        )
        _attach_stripe_gateway(app, tenant.id)
        calls: list[dict] = []

        def fake_post(url, **kwargs):
            calls.append({"url": url, **kwargs})
            return _FakeResponse({"id": "re_live_123"})

        monkeypatch.setattr(requests, "post", fake_post)

        result = PaymentService().refund(
            tenant_id=tenant.id,
            payment_public_id=str(payment.public_id),
            amount=Decimal("7.50"),
        )

        assert result["provider_refund_id"] == "re_live_123"
        assert len(calls) == 1
        assert calls[0]["data"]["amount"] == 750
        assert calls[0]["data"]["payment_intent"] == "pi_abc"
        assert calls[0]["headers"]["Idempotency-Key"] == f"orion-refund-{payment.id}"
        assert calls[0]["headers"]["Authorization"] == "Bearer sk_live_test"
        refund = Refund.query.filter_by(payment_id=payment.id).one()
        assert refund.provider_refund_id == "re_live_123"
        assert refund.amount == Decimal("7.50")
    finally:
        app.config["PAYMENT_LIVE_CALLS_ENABLED"] = previous


@pytest.mark.parametrize("provider", ["stripe", "paypal", "palpay", "bnpl"])
def test_each_adapter_refund_payment_is_unified_and_forwards_amount(
    app, monkeypatch, provider
):
    previous = app.config.get("PAYMENT_LIVE_CALLS_ENABLED")
    app.config["PAYMENT_LIVE_CALLS_ENABLED"] = True
    try:
        encrypted = CryptoService(app.config["ENCRYPTION_KEY"]).encrypt(
            json.dumps(
                {
                    "secret_key": "sk_live_test",
                    "client_id": "client",
                    "client_secret": "secret",
                    "api_key": "api_key_test",
                }
            )
        )
        calls: list[dict] = []

        def fake_post(url, **kwargs):
            calls.append({"url": url, **kwargs})
            if url.endswith("/v1/oauth2/token"):
                return _FakeResponse({"access_token": "tok"})
            return _FakeResponse({"id": f"refund_{provider}_123"})

        monkeypatch.setattr(requests, "post", fake_post)
        payment = SimpleNamespace(id=987, provider_payment_id="txn_abc", currency="ILS")

        if provider == "bnpl":
            from bnpl.bnpl_provider import BnplProvider

            row = BnplProvider(
                tenant_id=1,
                provider="tabby",
                is_enabled=True,
                api_credentials_encrypted=encrypted,
                config={"is_sandbox": False},
            )
            result = refund_bnpl(
                payment=payment, provider_row=row, amount=Decimal("6.25")
            )
        else:
            gateway = TenantPaymentGateway(
                tenant_id=1,
                provider=provider,
                display_name=provider,
                is_enabled=True,
                is_sandbox=False,
                credentials_encrypted=encrypted,
                status="active",
            )
            adapter = {
                "stripe": refund_stripe,
                "paypal": refund_paypal,
                "palpay": refund_palpay,
            }[provider]
            result = adapter(payment=payment, gateway=gateway, amount=Decimal("6.25"))

        assert set(result) >= {"success", "provider_refund_id", "uncertain"}
        assert result["success"] is True
        assert result["provider_refund_id"] == f"refund_{provider}_123"
        assert result["uncertain"] is False

        last = calls[-1]
        if provider == "stripe":
            assert last["data"]["amount"] == 625
        elif provider == "paypal":
            assert last["json"]["amount"]["value"] == "6.25"
        else:
            assert last["json"]["amount"] == "6.25"
        expected_key = f"orion-refund-{payment.id}"
        if provider == "bnpl":
            expected_key += "-tabby"
        assert last["headers"]["Idempotency-Key"] == expected_key
    finally:
        app.config["PAYMENT_LIVE_CALLS_ENABLED"] = previous
