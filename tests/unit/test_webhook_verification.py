"""AZ-0.4: Webhook signature verification tests."""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from webhook_svc.verification_service import WebhookVerificationService


def _sign_stripe(secret: str, raw: bytes, timestamp: int | None = None) -> str:
    ts = timestamp or int(time.time())
    to_sign = f"{ts}.{raw.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig},v0=legacy"


def _sign_hmac(secret: str, raw: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


class TestVerifyStripeSignature:
    SECRET = "whsec_test_secret"

    def test_valid_signature(self, app):
        raw = b'{"type":"payment_intent.succeeded"}'
        header = _sign_stripe(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert svc.verify_stripe_signature(raw, header, self.SECRET)

    def test_tampered_body(self, app):
        raw = b'{"type":"payment_intent.succeeded"}'
        header = _sign_stripe(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert not svc.verify_stripe_signature(
            b'{"type":"payment_intent.failed"}', header, self.SECRET
        )

    def test_wrong_secret(self, app):
        raw = b'{"type":"payment_intent.succeeded"}'
        header = _sign_stripe(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert not svc.verify_stripe_signature(raw, header, "whsec_wrong")

    def test_missing_signature_header(self, app):
        raw = b'{"type":"payment_intent.succeeded"}'
        svc = WebhookVerificationService()
        assert not svc.verify_stripe_signature(raw, None, self.SECRET)

    def test_expired_timestamp(self, app):
        raw = b'{"type":"payment_intent.succeeded"}'
        old_ts = int(time.time()) - 3600
        header = _sign_stripe(self.SECRET, raw, timestamp=old_ts)
        svc = WebhookVerificationService()
        assert not svc.verify_stripe_signature(raw, header, self.SECRET)

    def test_malformed_header(self, app):
        raw = b'{}'
        svc = WebhookVerificationService()
        assert not svc.verify_stripe_signature(raw, "not-a-valid-header", self.SECRET)

    def test_empty_secret(self, app):
        raw = b'{}'
        svc = WebhookVerificationService()
        assert not svc.verify_stripe_signature(raw, "t=1,v1=sig", "")

    def test_unicode_payload(self, app):
        raw = '{"note":"héllo wörld"}'.encode("utf-8")
        header = _sign_stripe(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert svc.verify_stripe_signature(raw, header, self.SECRET)


class TestVerifyHmacSignature:
    SECRET = "shared_secret_123"

    def test_valid_signature(self, app):
        raw = b'{"status":"authorized"}'
        sig = _sign_hmac(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert svc.verify_hmac_signature(raw, sig, self.SECRET)

    def test_tampered_body(self, app):
        raw = b'{"status":"authorized"}'
        sig = _sign_hmac(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert not svc.verify_hmac_signature(
            b'{"status":"declined"}', sig, self.SECRET
        )

    def test_wrong_secret(self, app):
        raw = b'{}'
        sig = _sign_hmac(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert not svc.verify_hmac_signature(raw, sig, "wrong_secret")

    def test_empty_signature(self, app):
        svc = WebhookVerificationService()
        assert not svc.verify_hmac_signature(b'{}', "", self.SECRET)

    def test_empty_secret(self, app):
        svc = WebhookVerificationService()
        assert not svc.verify_hmac_signature(b'{}', "sig", "")


class TestBootstrapTenantContext:
    def test_unknown_tenant_raises_not_found(self, app):
        svc = WebhookVerificationService()
        with pytest.raises(Exception):
            svc.bootstrap_tenant_context(99999)
