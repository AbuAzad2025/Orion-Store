"""BNPL provider integration boundary (wave 8 #62).

Tabby/Tamara sandbox stubs are retained for local development. Real charges
use each provider's REST endpoint with the tenant's encrypted credentials.
"""

from __future__ import annotations

from decimal import Decimal

from flask import current_app

from bnpl.bnpl_provider import BnplProvider
from integrations.payments._http import (
    credentials_present,
    endpoint_for,
    idempotency_key,
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

DEFAULT_ENDPOINTS = {
    "tabby": (
        "https://api.tabby.ai/api/v2/payments",
        "https://api.tabby.ai/api/v2/payments",
    ),
    "tamara": ("https://api.tamara.co/v1/orders", "https://api.tamara.co/v1/orders"),
}


def charge_bnpl(*, order: Order, provider_row: BnplProvider, amount: Decimal) -> dict:
    provider = provider_row.provider
    credentials = load_credentials(provider_row)
    api_key = credentials.get("api_key") or credentials.get("secret_key")
    sandbox = bool((provider_row.config or {}).get("is_sandbox", True))
    sandbox_url, live_url = DEFAULT_ENDPOINTS.get(
        provider,
        (f"https://api.{provider}.example/v1/charges",) * 2,
    )
    base = endpoint_for(provider_row, "BNPL_API_BASE_URL", sandbox_url, live_url)

    configured = credentials_present(provider_row, credentials)
    if not configured and not sandbox:
        return {"success": False, "error": "bnpl_credentials_missing"}
    if not live_calls_enabled():
        if not stub_allowed() and not sandbox:
            return {"success": False, "error": "bnpl_credentials_missing"}
        label = "test" if sandbox else "live"
        return {
            "success": True,
            "external_transaction_id": f"bnpl_{label}_{provider}_{order.id}",
            "installment_plan": {"installments": 4, "interval": "monthly"},
            "mode": "stub",
        }
    if not api_key:
        return {"success": False, "error": "bnpl_credentials_missing"}

    result = post_json(
        base,
        payload={
            "amount": f"{amount:.2f}",
            "currency": "ILS",
            "reference_id": str(order.id),
            "installments": 4,
        },
        headers={"Authorization": f"Bearer {api_key}"},
        idempotency=f"{idempotency_key(order)}-{provider}",
    )
    if not result["success"]:
        return result
    txn_id = provider_payment_id(result["data"])
    if not txn_id:
        return {"success": False, "error": "bnpl_missing_transaction_id"}
    current_app.logger.info(
        "bnpl charge created", extra={"order_id": order.id, "provider": provider}
    )
    return {
        "success": True,
        "external_transaction_id": txn_id,
        "installment_plan": {"installments": 4, "interval": "monthly"},
        "mode": "sandbox" if sandbox else "live",
    }


def refund_payment(
    *, payment: Payment, provider_row: BnplProvider, amount: Decimal
) -> dict:
    """Refund a BNPL transaction; returns the unified refund result dictionary."""
    provider = provider_row.provider
    credentials = load_credentials(provider_row)
    api_key = credentials.get("api_key") or credentials.get("secret_key")
    sandbox = bool((provider_row.config or {}).get("is_sandbox", True))
    sandbox_url, live_url = DEFAULT_ENDPOINTS.get(
        provider,
        (f"https://api.{provider}.example/v1/charges",) * 2,
    )
    base = endpoint_for(provider_row, "BNPL_API_BASE_URL", sandbox_url, live_url)

    if not live_calls_enabled():
        label = "test" if sandbox else "live"
        return {
            "success": True,
            "provider_refund_id": f"bnpl_re_{label}_{provider}_{payment.id}",
            "uncertain": False,
        }
    if not api_key:
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": False,
            "error": "bnpl_credentials_missing",
        }

    result = post_json(
        f"{base}/{payment.provider_payment_id}/refund",
        payload={
            "amount": f"{amount:.2f}",
            "currency": "ILS",
            "transaction_id": payment.provider_payment_id,
        },
        headers={"Authorization": f"Bearer {api_key}"},
        idempotency=f"{refund_idempotency_key(payment)}-{provider}",
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
            "error": "bnpl_missing_refund_id",
        }
    current_app.logger.info(
        "bnpl refund created", extra={"payment_id": payment.id, "provider": provider}
    )
    return {
        "success": True,
        "provider_refund_id": refund_id,
        "uncertain": False,
    }
