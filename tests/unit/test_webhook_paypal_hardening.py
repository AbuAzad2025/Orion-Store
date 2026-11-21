"""PayPal webhook signature hardening — rejects forged/legacy acceptance."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from webhook_svc.verification_service import WebhookVerificationService

SECRET = "paypal_webhook_secret"


def _headers(
    raw: bytes,
    *,
    secret: str = SECRET,
    transmitted_at: str | None = None,
    algo: str = "HMAC-SHA256",
    include_sig: bool = True,
) -> dict[str, str]:
    ts = transmitted_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    signed = "|".join(["txn-1", ts, "wh-1", raw.decode("utf-8")]).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    headers = {
        "Paypal-Auth-Algo": algo,
        "Paypal-Cert-Url": "https://api.paypal.com/certs",
        "Paypal-Transmit-Id": "txn-1",
        "Paypal-Transmit-Time": ts,
        "Paypal-Webhook-Id": "wh-1",
    }
    if include_sig:
        headers["Paypal-Transmit-Sig"] = sig
    return headers


def test_valid_signature_accepted(app):
    raw = b'{"event_type":"PAYMENT.CAPTURE.COMPLETED"}'
    assert WebhookVerificationService().verify_paypal_signature(
        raw, _headers(raw), SECRET
    )


def test_missing_signature_header_rejected(app):
    raw = b"{}"
    assert not WebhookVerificationService().verify_paypal_signature(
        raw, _headers(raw, include_sig=False), SECRET
    )


def test_unsupported_algorithm_rejected(app):
    raw = b"{}"
    assert not WebhookVerificationService().verify_paypal_signature(
        raw, _headers(raw, algo="SHA1"), SECRET
    )


def test_stale_timestamp_rejected(app):
    raw = b"{}"
    old = (
        (datetime.now(timezone.utc) - timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z")
    )
    assert not WebhookVerificationService().verify_paypal_signature(
        raw, _headers(raw, transmitted_at=old), SECRET
    )


def test_tampered_body_rejected(app):
    raw = b'{"amount":"10"}'
    headers = _headers(raw)
    assert not WebhookVerificationService().verify_paypal_signature(
        b'{"amount":"999"}', headers, SECRET
    )
