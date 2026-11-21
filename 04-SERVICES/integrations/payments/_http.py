"""Shared outbound payment HTTP boundary.

All provider adapters in this package use this module so that:
  * credentials are decrypted from the existing Fernet column,
  * every charge carries a stable idempotency key,
  * network failures become structured ``success=False`` results,
  * production never silently falls back to fake payment IDs.
"""

from __future__ import annotations

import json
from typing import Any

import requests
from flask import current_app

from core.crypto import CryptoError, CryptoService

DEFAULT_TIMEOUT = (5, 15)  # connect, read — seconds


class PaymentGatewayError(Exception):
    """Raised when a provider is misconfigured in production."""


def load_credentials(row: Any) -> dict[str, Any]:
    """Decrypt the gateway credential JSON; return {} when absent/invalid."""
    encrypted = getattr(row, "credentials_encrypted", None) or getattr(
        row, "api_credentials_encrypted", None
    )
    if not encrypted:
        return {}
    try:
        svc = CryptoService(current_app.config.get("ENCRYPTION_KEY"))
        payload = json.loads(svc.decrypt(encrypted))
    except (CryptoError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def gateway_config(row: Any) -> dict[str, Any]:
    config = getattr(row, "config", None)
    return config if isinstance(config, dict) else {}


def is_sandbox(row: Any) -> bool:
    return bool(getattr(row, "is_sandbox", True))


def stub_allowed() -> bool:
    """Sandbox stubs are only acceptable outside production."""
    return bool(current_app.config.get("PAYMENT_STUB_ALLOWED", False))


def live_calls_enabled() -> bool:
    """Real provider HTTP calls are opt-in and enabled only in production."""
    return bool(current_app.config.get("PAYMENT_LIVE_CALLS_ENABLED", False))


def credentials_present(row: Any, credentials: dict[str, Any]) -> bool:
    """A stored (even legacy) encrypted credential counts as configured."""
    encrypted = getattr(row, "credentials_encrypted", None) or getattr(
        row, "api_credentials_encrypted", None
    )
    return bool(credentials) or bool(encrypted)


def idempotency_key(order: Any) -> str:
    """Stable per order — retries of the same logical charge dedupe upstream."""
    return f"orion-order-{order.id}"


def refund_idempotency_key(payment: Any) -> str:
    """Stable per payment — retries of the same logical refund dedupe upstream."""
    return f"orion-refund-{payment.id}"


def endpoint_for(
    row: Any, env_name: str, sandbox_url: str, live_url: str
) -> str | None:
    configured = gateway_config(row).get("api_base_url")
    if configured:
        return str(configured).rstrip("/")
    from os import environ

    configured = environ.get(env_name)
    if configured:
        return configured.rstrip("/")
    return sandbox_url if is_sandbox(row) else live_url


def post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    idempotency: str,
) -> dict[str, Any]:
    """POST JSON to a provider and normalise the outcome."""
    request_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Idempotency-Key": idempotency,
        **headers,
    }
    try:
        response = requests.post(
            url, json=payload, headers=request_headers, timeout=DEFAULT_TIMEOUT
        )
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": f"provider_unreachable: {type(exc).__name__}",
            "uncertain": True,
        }

    if response.status_code >= 400:
        return {"success": False, "error": f"provider_http_{response.status_code}"}
    try:
        data = response.json()
    except ValueError:
        return {"success": False, "error": "provider_invalid_response"}
    if not isinstance(data, dict):
        return {"success": False, "error": "provider_invalid_response"}
    return {"success": True, "data": data}


def post_form(
    url: str,
    *,
    data: dict[str, Any],
    headers: dict[str, str],
    idempotency: str,
) -> dict[str, Any]:
    """POST form-encoded data (required by Stripe) and normalise outcome."""
    request_headers = {
        "Accept": "application/json",
        "Idempotency-Key": idempotency,
        **headers,
    }
    try:
        response = requests.post(
            url, data=data, headers=request_headers, timeout=DEFAULT_TIMEOUT
        )
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": f"provider_unreachable: {type(exc).__name__}",
            "uncertain": True,
        }
    if response.status_code >= 400:
        return {"success": False, "error": f"provider_http_{response.status_code}"}
    try:
        payload = response.json()
    except ValueError:
        return {"success": False, "error": "provider_invalid_response"}
    return (
        {"success": True, "data": payload}
        if isinstance(payload, dict)
        else {
            "success": False,
            "error": "provider_invalid_response",
        }
    )


def provider_payment_id(data: dict[str, Any]) -> str | None:
    for key in ("id", "payment_intent_id", "order_id", "transaction_id"):
        value = data.get(key)
        if value:
            return str(value)
    nested = data.get("payment_intent")
    if isinstance(nested, dict) and nested.get("id"):
        return str(nested["id"])
    return None


def provider_refund_id(data: dict[str, Any]) -> str | None:
    """Pull the provider's refund identifier out of a normalised response."""
    for key in ("id", "refund_id", "refundId", "transaction_id"):
        value = data.get(key)
        if value:
            return str(value)
    nested = data.get("refund")
    if isinstance(nested, dict) and nested.get("id"):
        return str(nested["id"])
    return None
