"""Stripe Connect integration boundary (wave 4 #42).

Sandbox stubs remain available for local development (``PAYMENT_STUB_ALLOWED``),
but production uses the real Stripe REST API with the tenant's encrypted key.
"""

from __future__ import annotations

from decimal import Decimal

from flask import current_app

from integrations.payments._http import (
    credentials_present,
    idempotency_key,
    is_sandbox,
    live_calls_enabled,
    load_credentials,
    post_form,
    provider_payment_id,
    provider_refund_id,
    refund_idempotency_key,
    stub_allowed,
)
from order.order import Order
from payment.payment import Payment
from platform_models.tenant_gateway import TenantPaymentGateway

STRIPE_API = "https://api.stripe.com/v1/payment_intents"
STRIPE_REFUNDS_API = "https://api.stripe.com/v1/refunds"


def charge_stripe(
    *,
    order: Order,
    gateway: TenantPaymentGateway,
    amount: Decimal,
    currency: str = "ILS",
) -> dict:
    credentials = load_credentials(gateway)
    secret_key = credentials.get("secret_key") or credentials.get("api_key")
    sandbox = is_sandbox(gateway)

    configured = credentials_present(gateway, credentials)
    if not configured and not sandbox:
        return {"success": False, "error": "stripe_credentials_missing"}
    if not live_calls_enabled():
        if not stub_allowed() and not sandbox:
            return {"success": False, "error": "stripe_credentials_missing"}
        prefix = "pi_test" if sandbox else "pi_live"
        return {
            "success": True,
            "provider_payment_id": f"{prefix}_{order.id}",
            "mode": "stub",
        }
    if not secret_key:
        return {"success": False, "error": "stripe_credentials_missing"}

    result = post_form(
        STRIPE_API,
        data={
            "amount": int((amount * 100).quantize(Decimal("1"))),
            "currency": currency,
            "metadata[order_id]": str(order.id),
            "description": f"Orion order {order.id}",
        },
        headers={"Authorization": f"Bearer {secret_key}"},
        idempotency=idempotency_key(order),
    )
    if not result["success"]:
        return result
    payment_id = provider_payment_id(result["data"])
    if not payment_id:
        return {"success": False, "error": "stripe_missing_payment_id"}
    current_app.logger.info("stripe charge created", extra={"order_id": order.id})
    return {
        "success": True,
        "provider_payment_id": payment_id,
        "mode": "sandbox" if sandbox else "live",
    }


def refund_payment(
    *,
    payment: Payment,
    gateway: TenantPaymentGateway,
    amount: Decimal,
    currency: str = "ILS",
) -> dict:
    """Refund a Stripe charge; returns the unified refund result dictionary."""
    credentials = load_credentials(gateway)
    secret_key = credentials.get("secret_key") or credentials.get("api_key")
    sandbox = is_sandbox(gateway)

    if not live_calls_enabled():
        prefix = "re_test" if sandbox else "re_live"
        return {
            "success": True,
            "provider_refund_id": f"{prefix}_{payment.id}",
            "uncertain": False,
        }
    if not secret_key:
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": False,
            "error": "stripe_credentials_missing",
        }

    result = post_form(
        STRIPE_REFUNDS_API,
        data={
            "payment_intent": payment.provider_payment_id or "",
            "amount": int((amount * 100).quantize(Decimal("1"))),
            "metadata[refund_for]": str(payment.id),
        },
        headers={"Authorization": f"Bearer {secret_key}"},
        idempotency=refund_idempotency_key(payment),
    )
    if not result["success"]:
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": bool(result.get("uncertain", False)),
            "error": result.get("error"),
        }
    refund_id = provider_refund_id(result["data"])
    if not refund_id:
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": False,
            "error": "stripe_missing_refund_id",
        }
    current_app.logger.info("stripe refund created", extra={"payment_id": payment.id})
    return {
        "success": True,
        "provider_refund_id": refund_id,
        "uncertain": False,
    }
