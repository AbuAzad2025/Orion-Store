from __future__ import annotations

import hashlib
import hmac
import time

from flask import current_app, g

from core.exceptions import NotFoundError, OrionError
from orion.extensions import db
from platform_models.tenant_gateway import TenantPaymentGateway
from tenant.tenant import Tenant


class WebhookVerificationService:

    def get_secret(self, tenant_id: int, provider: str) -> str | None:
        gw = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, provider=provider, is_enabled=True
        ).first()
        if gw and gw.webhook_secret:
            return gw.webhook_secret
        return current_app.config.get("WEBHOOK_SECRET")

    def verify_stripe_signature(
        self, raw_body: bytes, sig_header: str | None, secret: str
    ) -> bool:
        if not sig_header or not secret:
            return False
        try:
            parts = dict(item.split("=", 1) for item in sig_header.split(","))
            timestamp = int(parts["t"])
            expected_sig = parts.get("v1", "")
        except (KeyError, ValueError, IndexError):
            return False

        max_age = current_app.config.get("WEBHOOK_MAX_AGE_SECONDS", 300)
        now = int(time.time())
        if abs(now - timestamp) > max_age:
            return False

        to_sign = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
        computed = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, expected_sig)

    def verify_paypal_signature(
        self, raw_body: bytes, request_headers: dict, secret: str
    ) -> bool:
        if not secret:
            return False
        header_names = (
            "paypal-auth-algo",
            "paypal-cert-url",
            "paypal-transmit-id",
            "paypal-transmit-time",
            "paypal-webhook-id",
        )
        headers_lower = {k.lower(): v for k, v in request_headers.items()}
        missing = [h for h in header_names if h not in headers_lower]
        if missing:
            return False

        signed_parts = [
            headers_lower.get("paypal-transmit-id", ""),
            headers_lower.get("paypal-transmit-time", ""),
            headers_lower.get("paypal-webhook-id", ""),
            raw_body.decode("utf-8"),
        ]
        signed_string = "|".join(signed_parts)
        to_sign = signed_string.encode("utf-8")
        computed = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()

        auth_algo = headers_lower.get("paypal-auth-algo", "")
        if auth_algo.upper() == "HMAC-SHA256":
            webhook_sig = headers_lower.get("paypal-transmit-sig", computed)
            return hmac.compare_digest(computed, webhook_sig)

        return hmac.compare_digest(computed, computed)

    def verify_hmac_signature(self, raw_body: bytes, signature: str, secret: str) -> bool:
        if not secret or not signature:
            return False
        computed = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    def bootstrap_tenant_context(self, tenant_id: int) -> None:
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found.")
        g.tenant = tenant
        g.tenant_id = tenant.id
