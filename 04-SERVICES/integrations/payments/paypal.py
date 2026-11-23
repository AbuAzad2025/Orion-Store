"""PayPal integration boundary (wave 8 #62).

Uses the PayPal REST v2 orders API when credentials are configured. Local
development may keep the deterministic sandbox stub via PAYMENT_STUB_ALLOWED.
"""

from __future__ import annotations

import base64
from decimal import Decimal

from flask import current_app

from integrations.payments._http import (
    credentials_present,
    endpoint_for,
    idempotency_key,
    is_production,
    is_sandbox,
    live_calls_enabled,
    load_credentials,
    post_form,
    post_json,
    provider_payment_id,
    provider_refund_id,
    refund_idempotency_key,
    stub_allowed,
)
from order.order import Order
from payment.payment import Payment
from platform_models.tenant_gateway import TenantPaymentGateway

SANDBOX = "https://api-m.sandbox.paypal.com"
LIVE = "https://api-m.paypal.com"


def _access_token(base: str, client_id: str, secret: str) -> str | None:
    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    result = post_form(
        f"{base}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {basic}"},
        idempotency=f"paypal-token-{client_id[:8]}",
    )
    if not result["success"]:
        return None
    token = result["data"].get("access_token")
    return str(token) if token else None


def charge_paypal(
    *,
    order: Order,
    gateway: TenantPaymentGateway,
    amount: Decimal,
    currency: str = "ILS",
) -> dict:
    credentials = load_credentials(gateway)
    client_id = credentials.get("client_id")
    secret = credentials.get("client_secret") or credentials.get("secret_key")
    base = endpoint_for(gateway, "PAYPAL_API_BASE_URL", SANDBOX, LIVE)

    sandbox = is_sandbox(gateway)
    configured = credentials_present(gateway, credentials)
    if not configured and not sandbox:
        return {"success": False, "error": "paypal_credentials_missing"}
    if not live_calls_enabled():
        if is_production():
            return {"success": False, "error": "payment_provider_not_configured"}
        if not stub_allowed():
            return {"success": False, "error": "paypal_credentials_missing"}
        prefix = "pp_test" if sandbox else "pp_live"
        return {
            "success": True,
            "provider_payment_id": f"{prefix}_{order.id}",
            "mode": "stub",
        }
    if not client_id or not secret:
        return {"success": False, "error": "paypal_credentials_missing"}

    token = _access_token(base, client_id, secret)
    if not token:
        return {"success": False, "error": "paypal_auth_failed"}

    created = post_json(
        f"{base}/v2/checkout/orders",
        payload={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": str(order.id),
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}",
                    },
                }
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
        idempotency=idempotency_key(order),
    )
    if not created["success"]:
        return created
    order_id = provider_payment_id(created["data"])
    if not order_id:
        return {"success": False, "error": "paypal_order_id_missing"}

    captured = post_json(
        f"{base}/v2/checkout/orders/{order_id}/capture",
        payload={},
        headers={"Authorization": f"Bearer {token}"},
        idempotency=f"{idempotency_key(order)}-capture",
    )
    if not captured["success"]:
        return captured
    current_app.logger.info("paypal order captured", extra={"order_id": order.id})
    return {
        "success": True,
        "provider_payment_id": order_id,
        "mode": "sandbox" if is_sandbox(gateway) else "live",
    }


def refund_payment(
    *,
    payment: Payment,
    gateway: TenantPaymentGateway,
    amount: Decimal,
    currency: str = "ILS",
) -> dict:
    """Refund a captured PayPal payment; returns the unified refund result."""
    credentials = load_credentials(gateway)
    client_id = credentials.get("client_id")
    secret = credentials.get("client_secret") or credentials.get("secret_key")
    base = endpoint_for(gateway, "PAYPAL_API_BASE_URL", SANDBOX, LIVE)

    if not live_calls_enabled():
        if is_production():
            return {"success": False, "error": "payment_provider_not_configured"}
        prefix = "pp_re_test" if is_sandbox(gateway) else "pp_re_live"
        return {
            "success": True,
            "provider_refund_id": f"{prefix}_{payment.id}",
            "uncertain": False,
        }
    if not client_id or not secret:
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": False,
            "error": "paypal_credentials_missing",
        }

    token = _access_token(base, client_id, secret)
    if not token:
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": False,
            "error": "paypal_auth_failed",
        }

    result = post_json(
        f"{base}/v2/payments/captures/{payment.provider_payment_id}/refund",
        payload={"amount": {"currency_code": currency, "value": f"{amount:.2f}"}},
        headers={"Authorization": f"Bearer {token}"},
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
            "error": "paypal_missing_refund_id",
        }
    current_app.logger.info("paypal refund created", extra={"payment_id": payment.id})
    return {
        "success": True,
        "provider_refund_id": refund_id,
        "uncertain": False,
    }
