"""PalPay payment boundary (§1.6, wave 15)."""

from __future__ import annotations

from decimal import Decimal

from flask import current_app

from integrations.payments._http import (
    credentials_present,
    endpoint_for,
    idempotency_key,
    is_sandbox,
    live_calls_enabled,
    load_credentials,
    post_json,
    provider_payment_id,
    provider_refund_id,
    refund_idempotency_key,
    stub_allowed,
)
from order.order import Order
from payment.payment import Payment
from platform_models.tenant_gateway import TenantPaymentGateway

SANDBOX_URL = "https://sandbox.palpay.ps/api/v1"
LIVE_URL = "https://api.palpay.ps/api/v1"


def charge_palpay(
    *, order: Order, gateway: TenantPaymentGateway, amount: Decimal
) -> dict:
    credentials = load_credentials(gateway)
    api_key = credentials.get("api_key") or credentials.get("secret_key")
    base = endpoint_for(gateway, "PALPAY_API_BASE_URL", SANDBOX_URL, LIVE_URL)

    sandbox = is_sandbox(gateway)
    configured = credentials_present(gateway, credentials)
    if not configured and not sandbox:
        return {"success": False, "error": "palpay_credentials_missing"}
    if not live_calls_enabled():
        if not stub_allowed() and not sandbox:
            return {"success": False, "error": "palpay_credentials_missing"}
        prefix = "palpay_test" if sandbox else "palpay_live"
        return {
            "success": True,
            "provider_payment_id": f"{prefix}_{order.id}",
            "mode": "stub",
        }
    if not api_key:
        return {"success": False, "error": "palpay_credentials_missing"}

    result = post_json(
        f"{base}/charges",
        payload={
            "amount": f"{amount:.2f}",
            "currency": "ILS",
            "merchant_reference": str(order.id),
        },
        headers={"Authorization": f"Bearer {api_key}"},
        idempotency=idempotency_key(order),
    )
    if not result["success"]:
        return result
    payment_id = provider_payment_id(result["data"])
    if not payment_id:
        return {"success": False, "error": "palpay_missing_payment_id"}
    current_app.logger.info("palpay charge created", extra={"order_id": order.id})
    return {
        "success": True,
        "provider_payment_id": payment_id,
        "mode": "sandbox" if is_sandbox(gateway) else "live",
    }


def refund_payment(
    *, payment: Payment, gateway: TenantPaymentGateway, amount: Decimal
) -> dict:
    """Refund a PalPay charge; returns the unified refund result dictionary."""
    credentials = load_credentials(gateway)
    api_key = credentials.get("api_key") or credentials.get("secret_key")
    base = endpoint_for(gateway, "PALPAY_API_BASE_URL", SANDBOX_URL, LIVE_URL)

    if not live_calls_enabled():
        prefix = "palpay_re_test" if is_sandbox(gateway) else "palpay_re_live"
        return {
            "success": True,
            "provider_refund_id": f"{prefix}_{payment.id}",
            "uncertain": False,
        }
    if not api_key:
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": False,
            "error": "palpay_credentials_missing",
        }

    result = post_json(
        f"{base}/charges/{payment.provider_payment_id}/refund",
        payload={"amount": f"{amount:.2f}", "currency": "ILS"},
        headers={"Authorization": f"Bearer {api_key}"},
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
            "error": "palpay_missing_refund_id",
        }
    current_app.logger.info("palpay refund created", extra={"payment_id": payment.id})
    return {
        "success": True,
        "provider_refund_id": refund_id,
        "uncertain": False,
    }
