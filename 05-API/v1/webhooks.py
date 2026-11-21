"""Webhook handlers (wave 4 #44) — verification, replay guard, real effects."""

from __future__ import annotations

from app_platform.app_platform import AppWebhookSubscription
from flask import Blueprint, jsonify, request
from webhook_svc.verification_service import WebhookVerificationService
from webhook_svc.webhook_handler import WebhookEffectHandler

from core.exceptions import OrionError
from core.middleware import bind_rls_context

webhooks_bp = Blueprint("webhooks", __name__)
_svc = WebhookVerificationService()
_effects = WebhookEffectHandler()

STRIPE_REFUND_EVENTS = ("charge.refunded", "refund.updated", "refund.created")
PAYPAL_REFUND_EVENTS = (
    "PAYMENT.CAPTURE.REFUNDED",
    "REFUND.PAYMENT_REFUND_COMPLETED",
)


def _event_id(payload: dict, fallback: str | None = None) -> str | None:
    value = payload.get("id") or payload.get("event_id") or fallback
    return str(value) if value else None


def _effect_response(tenant_id: int, event_type: str, result: dict | None):
    """Translate a handler result into an HTTP response.

    An event we recognise but cannot apply (e.g. a charge with no matching
    pending payment) is still acknowledged — providers retry on 5xx, not on
    an explicit "ignored" acknowledgement.
    """
    if not result or not result.get("processed"):
        body = {"received": True, "tenant_id": tenant_id, "ignored": event_type}
        if result and result.get("reason"):
            body["reason"] = result["reason"]
        return jsonify(body), 200
    return jsonify({"received": True, "tenant_id": tenant_id, "effect": result}), 200


@webhooks_bp.get("/status")
def webhooks_status():
    return {"blueprint": "webhooks", "status": "active"}, 200


@webhooks_bp.post("/stripe/<int:tenant_id>")
def stripe_webhook(tenant_id: int):
    try:
        raw = request.get_data()
        sig = request.headers.get("Stripe-Signature")
        secret = _svc.get_secret(tenant_id, "stripe")
        if not secret or not _svc.verify_stripe_signature(raw, sig, secret):
            return jsonify({"error": "Invalid signature."}), 400
        payload = request.get_json(silent=True) or {}
        if not _svc.claim_webhook_event("stripe", _event_id(payload)):
            return jsonify({"received": True, "duplicate": True}), 200
        _svc.bootstrap_tenant_context(tenant_id)
        bind_rls_context()
        event_type = payload.get("type", "unknown")
        if event_type == "payment_intent.succeeded":
            result = _effects.handle_stripe_payment_succeeded(tenant_id, payload)
        elif event_type in STRIPE_REFUND_EVENTS:
            result = _effects.handle_refund(tenant_id, payload, provider="stripe")
        else:
            result = None
        return _effect_response(tenant_id, event_type, result)
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@webhooks_bp.post("/paypal/<int:tenant_id>")
def paypal_webhook(tenant_id: int):
    try:
        raw = request.get_data()
        secret = _svc.get_secret(tenant_id, "paypal")
        headers = dict(request.headers)
        if not secret or not _svc.verify_paypal_signature(raw, headers, secret):
            return jsonify({"error": "Invalid signature."}), 400
        payload = request.get_json(silent=True) or {}
        if not _svc.claim_webhook_event(
            "paypal",
            _event_id(payload, headers.get("Paypal-Transmission-Id")),
        ):
            return jsonify({"received": True, "duplicate": True}), 200
        _svc.bootstrap_tenant_context(tenant_id)
        bind_rls_context()
        event_type = payload.get("event_type", "unknown")
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            result = _effects.handle_paypal_capture_completed(tenant_id, payload)
        elif event_type in PAYPAL_REFUND_EVENTS:
            result = _effects.handle_refund(tenant_id, payload, provider="paypal")
        elif event_type == "CHECKOUT.ORDER.APPROVED":
            # Approval is not money captured yet — acknowledge without effect.
            result = None
        else:
            result = None
        return _effect_response(tenant_id, event_type, result)
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@webhooks_bp.post("/bnpl/<provider>/<int:tenant_id>")
def bnpl_webhook(provider: str, tenant_id: int):
    try:
        raw = request.get_data()
        sig = request.headers.get("X-Webhook-Signature", "")
        secret = _svc.get_secret(tenant_id, provider)
        if not secret or not _svc.verify_hmac_signature(raw, sig, secret):
            return jsonify({"error": "Invalid signature."}), 400
        payload = request.get_json(silent=True) or {}
        if not _svc.claim_webhook_event(
            f"bnpl:{provider}", _event_id(payload, request.headers.get("X-Event-Id"))
        ):
            return jsonify({"received": True, "duplicate": True}), 200
        _svc.bootstrap_tenant_context(tenant_id)
        bind_rls_context()
        status = payload.get("status", "unknown")
        if status == "captured":
            result = _effects.handle_bnpl_captured(
                tenant_id, payload, provider=provider
            )
        elif status == "refunded":
            result = _effects.handle_refund(
                tenant_id, payload, provider=f"bnpl:{provider}"
            )
        elif status == "authorized":
            # Authorisation alone is not a capture — no financial effect yet.
            result = None
        else:
            result = None
        return _effect_response(tenant_id, status, result)
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@webhooks_bp.post("/palpay/<int:tenant_id>")
def palpay_webhook(tenant_id: int):
    """PalPay uses the same HMAC + status contract as the BNPL gateways."""
    return bnpl_webhook("palpay", tenant_id)


@webhooks_bp.post("/app/<int:tenant_id>/<event_type>")
def app_webhook(tenant_id: int, event_type: str):
    """App-platform webhook dispatcher.

    Verifies the HMAC signature using the subscription's signing secret and
    acknowledges receipt. This dispatcher has **no financial effect** — payment
    handlers above remain untouched. An unrecognised or unsigned event never
    reaches any effect handler.
    """
    try:
        raw = request.get_data()
        signature = request.headers.get("X-Webhook-Signature", "")

        # Establish tenant context before querying the RLS-protected table.
        _svc.bootstrap_tenant_context(tenant_id)
        bind_rls_context()

        subscription = AppWebhookSubscription.query.filter_by(
            tenant_id=tenant_id, topic=event_type, is_active=True
        ).first()
        if not subscription or not subscription.webhook_secret:
            return jsonify({"error": "No active subscription for this event."}), 404
        if not _svc.verify_hmac_signature(raw, signature, subscription.webhook_secret):
            return jsonify({"error": "Invalid signature."}), 400

        payload = request.get_json(silent=True) or {}
        if not _svc.claim_webhook_event(
            f"app:{tenant_id}:{event_type}",
            _event_id(payload, request.headers.get("X-Event-Id")),
        ):
            return jsonify({"received": True, "duplicate": True}), 200

        return (
            jsonify(
                {
                    "received": True,
                    "tenant_id": tenant_id,
                    "event_type": event_type,
                    "subscription_id": subscription.id,
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
