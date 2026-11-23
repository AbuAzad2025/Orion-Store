"""Shared outbound payment HTTP boundary.

All provider adapters in this package use this module so that:
  * credentials are decrypted from the existing Fernet column,
  * every charge carries a stable idempotency key,
  * network failures become structured ``success=False`` results,
  * production never silently falls back to fake payment IDs.
"""

from __future__ import annotations

import ipaddress
import json
from typing import Any
from urllib.parse import urlparse

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


def is_production() -> bool:
    """True only for a production deployment (never for testing/development)."""
    env = str(current_app.config.get("ENV") or "").lower()
    return env in ("production", "prod")


def stub_allowed() -> bool:
    """Sandbox stubs are never acceptable in production, even if flag is set."""
    if is_production():
        return False
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


def _safe_endpoint(url: str, default_url: str) -> str:
    """Only allow HTTPS on the provider's own host — no redirects elsewhere."""
    parsed = urlparse(url)
    expected = urlparse(default_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.hostname.lower() != (expected.hostname or "").lower()
    ):
        raise PaymentGatewayError("invalid_payment_endpoint")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass  # a DNS name, not a literal private address
    else:
        if address.is_private or address.is_loopback or address.is_link_local:
            raise PaymentGatewayError("invalid_payment_endpoint")
    return url.rstrip("/")


def endpoint_for(
    row: Any, env_name: str, sandbox_url: str, live_url: str
) -> str | None:
    """Resolve a provider base URL. Tenants may never override it.

    ``config.api_base_url`` used to be caller-writable, which allowed an SSRF
    and credential exfiltration from any tenant that could edit gateway
    config. Only the operator-controlled environment variable is honoured,
    and it must still point at the provider's own HTTPS host.
    """
    default = sandbox_url if is_sandbox(row) else live_url
    import os

    configured = os.environ.get(env_name)
    if configured:
        return _safe_endpoint(configured.rstrip("/"), default)
    return default


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
            url,
            json=payload,
            headers=request_headers,
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=False,
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
            url,
            data=data,
            headers=request_headers,
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=False,
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
