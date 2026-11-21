from __future__ import annotations

import base64
import hashlib
import hmac
import time
import zlib
from urllib.parse import urlparse

import requests
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from flask import current_app, g

from core.exceptions import NotFoundError, OrionError
from orion.extensions import db
from platform_models.tenant_gateway import TenantPaymentGateway
from tenant.tenant import Tenant

# PayPal publishes its signing certificates only on these hosts. Anything else
# (including look-alike domains) must never be used as a trust anchor.
PAYPAL_CERT_HOST_ALLOWLIST = frozenset({"api-m.paypal.com", "api-m.sandbox.paypal.com"})
PAYPAL_CERT_FETCH_TIMEOUT_SECONDS = 5

_PAYPAL_REQUIRED_HEADERS = (
    "paypal-auth-algo",
    "paypal-cert-url",
    "paypal-transmit-id",
    "paypal-transmit-time",
    "paypal-transmit-sig",
    "paypal-webhook-id",
)


class WebhookVerificationService:

    def get_secret(self, tenant_id: int, provider: str) -> str | None:
        gw = TenantPaymentGateway.query.filter_by(
            tenant_id=tenant_id, provider=provider, is_enabled=True
        ).first()
        if gw and gw.webhook_secret:
            return gw.webhook_secret
        # A shared secret across tenants allows cross-tenant event forgery.
        if current_app.config.get("ENV") == "production":
            return None
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
        """Verify a PayPal webhook signature.

        Production uses PayPal's real scheme: ``SHA256withRSA`` verified with
        the public key of a certificate fetched from an allowlisted PayPal host.
        Local/development/testing keeps the deterministic HMAC-SHA256 path.

        Unsupported algorithms, unexpected certificate hosts, missing headers
        and stale timestamps are always rejected (never accepted by default).
        """
        headers_lower = {k.lower(): v for k, v in request_headers.items()}
        if any(h not in headers_lower for h in _PAYPAL_REQUIRED_HEADERS):
            return False

        if not self._paypal_timestamp_fresh(headers_lower["paypal-transmit-time"]):
            return False

        if current_app.config.get("ENV") == "production":
            return self._verify_paypal_rsa_signature(raw_body, headers_lower)

        # Testing/development — unchanged HMAC path used by the existing suite.
        if not secret:
            return False
        if headers_lower["paypal-auth-algo"].upper() != "HMAC-SHA256":
            return False

        signed_parts = [
            headers_lower["paypal-transmit-id"],
            headers_lower["paypal-transmit-time"],
            headers_lower["paypal-webhook-id"],
            raw_body.decode("utf-8"),
        ]
        to_sign = "|".join(signed_parts).encode("utf-8")
        computed = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, headers_lower["paypal-transmit-sig"])

    def _verify_paypal_rsa_signature(
        self, raw_body: bytes, headers: dict[str, str]
    ) -> bool:
        """Verify PayPal's RSA-SHA256 signature against its published cert."""
        if headers["paypal-auth-algo"].upper() != "SHA256WITHRSA":
            return False

        cert_url = headers["paypal-cert-url"]
        if not self._paypal_cert_url_allowed(cert_url):
            return False

        try:
            signature = base64.b64decode(headers["paypal-transmit-sig"], validate=True)
        except (ValueError, TypeError):
            return False

        try:
            certificate = x509.load_pem_x509_certificate(
                self._fetch_paypal_certificate(cert_url)
            )
            public_key = certificate.public_key()
            if not isinstance(public_key, rsa.RSAPublicKey):
                return False

            signed = "|".join(
                (
                    headers["paypal-transmit-id"],
                    headers["paypal-transmit-time"],
                    headers["paypal-webhook-id"],
                    str(zlib.crc32(raw_body) & 0xFFFFFFFF),
                )
            ).encode("utf-8")
            public_key.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
            return True
        except (InvalidSignature, ValueError, TypeError, requests.RequestException):
            # Any failure to fetch/parse the cert or verify the signature fails
            # closed in production.
            return False

    @staticmethod
    def _paypal_cert_url_allowed(url: str) -> bool:
        """Only HTTPS URLs on the exact PayPal API hosts are trusted."""
        try:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                return False
            if parsed.username or parsed.password:
                return False
            if parsed.port not in (None, 443):
                return False
            return parsed.hostname.lower() in PAYPAL_CERT_HOST_ALLOWLIST
        except (ValueError, TypeError, AttributeError):
            return False

    @staticmethod
    def _fetch_paypal_certificate(url: str) -> bytes:
        # Never follow redirects: a trusted host must not be able to bounce the
        # certificate fetch to a domain outside the allowlist.
        response = requests.get(
            url,
            timeout=PAYPAL_CERT_FETCH_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        response.raise_for_status()
        content = response.content
        return content.encode("utf-8") if isinstance(content, str) else content

    @staticmethod
    def _paypal_timestamp_fresh(value: str) -> bool:
        """Reject stale PayPal notifications (replay protection)."""
        from datetime import datetime, timezone

        try:
            # PayPal may send ISO-8601; older clients send Unix epoch seconds.
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - parsed).total_seconds()
        except (ValueError, TypeError, OverflowError, AttributeError):
            return False
        max_age = current_app.config.get("WEBHOOK_MAX_AGE_SECONDS", 300)
        return 0 <= age <= max_age

    def verify_hmac_signature(
        self, raw_body: bytes, signature: str, secret: str
    ) -> bool:
        if not secret or not signature:
            return False
        computed = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    def claim_webhook_event(self, provider: str, event_id: str | None) -> bool:
        """Atomically claim a webhook event id to prevent replay.

        Returns True when the event should be processed. In production a
        missing Redis backend fails closed (event is rejected); in local
        development the event is allowed so the stack stays runnable offline.
        """
        if not event_id:
            # Without an id replay cannot be detected — fail closed in production.
            return current_app.config.get("ENV") != "production"
        cache = current_app.extensions.get("redis_cache")
        if cache is None or not cache.available:
            return current_app.config.get("ENV") != "production"
        return cache.set_nx(f"webhook:{provider}:{event_id}", "1")

    def bootstrap_tenant_context(self, tenant_id: int) -> None:
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found.")
        g.tenant = tenant
        g.tenant_id = tenant.id
