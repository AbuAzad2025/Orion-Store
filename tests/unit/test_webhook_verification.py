"""AZ-0.4: Webhook signature verification tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import zlib
from datetime import datetime, timedelta, timezone

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
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
        raw = b"{}"
        svc = WebhookVerificationService()
        assert not svc.verify_stripe_signature(raw, "not-a-valid-header", self.SECRET)

    def test_empty_secret(self, app):
        raw = b"{}"
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
        assert not svc.verify_hmac_signature(b'{"status":"declined"}', sig, self.SECRET)

    def test_wrong_secret(self, app):
        raw = b"{}"
        sig = _sign_hmac(self.SECRET, raw)
        svc = WebhookVerificationService()
        assert not svc.verify_hmac_signature(raw, sig, "wrong_secret")

    def test_empty_signature(self, app):
        svc = WebhookVerificationService()
        assert not svc.verify_hmac_signature(b"{}", "", self.SECRET)

    def test_empty_secret(self, app):
        svc = WebhookVerificationService()
        assert not svc.verify_hmac_signature(b"{}", "sig", "")


class TestBootstrapTenantContext:
    def test_unknown_tenant_raises_not_found(self, app):
        svc = WebhookVerificationService()
        with pytest.raises(Exception):
            svc.bootstrap_tenant_context(99999)


# ---------------------------------------------------------------------------
# PayPal — production RSA (SHA256withRSA) verification
# ---------------------------------------------------------------------------


def _rsa_signing_material():
    """Return a self-signed cert (PEM) and its RSA private key for tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "api-m.paypal.com")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM), key


def _paypal_rsa_headers(
    raw: bytes,
    key,
    *,
    cert_url: str = "https://api-m.paypal.com/certs",
    algo: str = "SHA256withRSA",
    transmitted_at: str | None = None,
    sig_override: bytes | None = None,
) -> dict[str, str]:
    ts = transmitted_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    signed = "|".join(
        (
            "txn-rsa-1",
            ts,
            "wh-rsa-1",
            str(zlib.crc32(raw) & 0xFFFFFFFF),
        )
    ).encode("utf-8")
    signature = sig_override or key.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    return {
        "Paypal-Auth-Algo": algo,
        "Paypal-Cert-Url": cert_url,
        "Paypal-Transmit-Id": "txn-rsa-1",
        "Paypal-Transmit-Time": ts,
        "Paypal-Webhook-Id": "wh-rsa-1",
        # PayPal transmits the RSA signature base64-encoded.
        "Paypal-Transmit-Sig": base64.b64encode(signature).decode("ascii"),
    }


def _mock_cert_fetch(monkeypatch, pem: bytes):
    """Replace requests.get with a local stub; returns the captured URL list."""
    calls: list[str] = []

    class _Response:
        status_code = 200
        content = pem

        def raise_for_status(self):
            return None

    def _get(url, **kwargs):
        calls.append(url)
        return _Response()

    monkeypatch.setattr(requests, "get", _get)
    return calls


class TestVerifyPaypalSignatureRSA:
    """Production uses the real PayPal RSA scheme, never HMAC."""

    @pytest.fixture
    def production_app(self, app):
        original = app.config.get("ENV")
        app.config["ENV"] = "production"
        yield app
        if original is None:
            app.config.pop("ENV", None)
        else:
            app.config["ENV"] = original

    @pytest.fixture
    def material(self):
        return _rsa_signing_material()

    def test_valid_rsa_signature_accepted(self, production_app, monkeypatch, material):
        pem, key = material
        calls = _mock_cert_fetch(monkeypatch, pem)
        raw = b'{"event_type":"PAYMENT.CAPTURE.COMPLETED"}'
        headers = _paypal_rsa_headers(raw, key)
        assert WebhookVerificationService().verify_paypal_signature(
            raw, headers, "unused-in-production"
        )
        assert calls == ["https://api-m.paypal.com/certs"]

    def test_forged_rsa_signature_rejected(self, production_app, monkeypatch, material):
        pem, _ = material
        _mock_cert_fetch(monkeypatch, pem)
        raw = b'{"event_type":"PAYMENT.CAPTURE.COMPLETED"}'
        # Signed by an attacker's key while the cert comes from PayPal.
        _, attacker_key = _rsa_signing_material()
        headers = _paypal_rsa_headers(raw, attacker_key)
        assert not WebhookVerificationService().verify_paypal_signature(
            raw, headers, "unused-in-production"
        )

    def test_tampered_body_rejected(self, production_app, monkeypatch, material):
        pem, key = material
        _mock_cert_fetch(monkeypatch, pem)
        raw = b'{"amount":"10"}'
        headers = _paypal_rsa_headers(raw, key)
        assert not WebhookVerificationService().verify_paypal_signature(
            b'{"amount":"999"}', headers, "unused-in-production"
        )

    @pytest.mark.parametrize(
        "cert_url",
        [
            "https://evil.example.com/cert",
            "https://api-m.paypal.com.evil.example.com/cert",
            "http://api-m.paypal.com/cert",
            "https://user@api-m.paypal.com/cert",
        ],
    )
    def test_cert_url_outside_allowlist_rejected(
        self, production_app, monkeypatch, material, cert_url
    ):
        pem, key = material
        calls = _mock_cert_fetch(monkeypatch, pem)
        raw = b"{}"
        headers = _paypal_rsa_headers(raw, key, cert_url=cert_url)
        assert not WebhookVerificationService().verify_paypal_signature(
            raw, headers, "unused-in-production"
        )
        # A rejected URL must never trigger a network request.
        assert calls == []

    def test_sandbox_cert_host_accepted(self, production_app, monkeypatch, material):
        pem, key = material
        calls = _mock_cert_fetch(monkeypatch, pem)
        raw = b"{}"
        headers = _paypal_rsa_headers(
            raw, key, cert_url="https://api-m.sandbox.paypal.com/certs"
        )
        assert WebhookVerificationService().verify_paypal_signature(
            raw, headers, "unused-in-production"
        )
        assert calls == ["https://api-m.sandbox.paypal.com/certs"]

    def test_unsupported_algo_rejected_in_production(
        self, production_app, monkeypatch, material
    ):
        pem, key = material
        calls = _mock_cert_fetch(monkeypatch, pem)
        raw = b"{}"
        headers = _paypal_rsa_headers(raw, key, algo="HMAC-SHA256")
        assert not WebhookVerificationService().verify_paypal_signature(
            raw, headers, "unused-in-production"
        )
        assert calls == []

    def test_stale_timestamp_rejected_in_production(
        self, production_app, monkeypatch, material
    ):
        pem, key = material
        calls = _mock_cert_fetch(monkeypatch, pem)
        raw = b"{}"
        old = (
            (datetime.now(timezone.utc) - timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z")
        )
        headers = _paypal_rsa_headers(raw, key, transmitted_at=old)
        assert not WebhookVerificationService().verify_paypal_signature(
            raw, headers, "unused-in-production"
        )
        assert calls == []

    def test_hmac_still_works_in_testing(self, app, material):
        """The non-production HMAC path remains intact for local/CI runs."""
        assert app.config.get("ENV") != "production"
        raw = b'{"event_type":"PAYMENT.CAPTURE.COMPLETED"}'
        secret = "paypal_webhook_secret"
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        signed = "|".join(("txn-1", ts, "wh-1", raw.decode("utf-8"))).encode("utf-8")
        sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        headers = {
            "Paypal-Auth-Algo": "HMAC-SHA256",
            "Paypal-Cert-Url": "https://example.com/cert",
            "Paypal-Transmit-Id": "txn-1",
            "Paypal-Transmit-Time": ts,
            "Paypal-Webhook-Id": "wh-1",
            "Paypal-Transmit-Sig": sig,
        }
        assert WebhookVerificationService().verify_paypal_signature(
            raw, headers, secret
        )
