"""Webhook handlers (wave 4 #44) — AZ-0.4: signature verification."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from webhook_svc.verification_service import WebhookVerificationService

webhooks_bp = Blueprint("webhooks", __name__)
_svc = WebhookVerificationService()


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
        _svc.bootstrap_tenant_context(tenant_id)
        payload = request.get_json(silent=True) or {}
        event_type = payload.get("type", "unknown")
        if event_type == "payment_intent.succeeded":
            return jsonify({"received": True, "tenant_id": tenant_id}), 200
        return jsonify({"received": True, "ignored": event_type}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@webhooks_bp.post("/paypal/<int:tenant_id>")
def paypal_webhook(tenant_id: int):
    try:
        raw = request.get_data()
        secret = _svc.get_secret(tenant_id, "paypal")
        if not secret or not _svc.verify_paypal_signature(
            raw, dict(request.headers), secret
        ):
            return jsonify({"error": "Invalid signature."}), 400
        _svc.bootstrap_tenant_context(tenant_id)
        payload = request.get_json(silent=True) or {}
        event_type = payload.get("event_type", "unknown")
        if event_type in ("PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"):
            return jsonify({"received": True, "tenant_id": tenant_id}), 200
        return jsonify({"received": True, "ignored": event_type}), 200
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
        _svc.bootstrap_tenant_context(tenant_id)
        payload = request.get_json(silent=True) or {}
        status = payload.get("status", "unknown")
        if status in ("authorized", "captured"):
            return jsonify({"received": True, "tenant_id": tenant_id}), 200
        return jsonify({"received": True, "ignored": status}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
