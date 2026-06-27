"""Webhook handlers (wave 4 #44)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.get("/status")
def webhooks_status():
    return {"blueprint": "webhooks", "status": "active"}, 200


@webhooks_bp.post("/paypal/<int:tenant_id>")
def paypal_webhook(tenant_id: int):
    payload = request.get_json(silent=True) or {}
    event_type = payload.get("event_type", "unknown")
    if event_type in ("PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"):
        return jsonify({"received": True, "tenant_id": tenant_id}), 200
    return jsonify({"received": True, "ignored": event_type}), 200


@webhooks_bp.post("/bnpl/<provider>/<int:tenant_id>")
def bnpl_webhook(provider: str, tenant_id: int):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status", "unknown")
    if status in ("authorized", "captured"):
        return jsonify({"received": True, "tenant_id": tenant_id}), 200
    return jsonify({"received": True, "ignored": status}), 200


@webhooks_bp.post("/stripe/<int:tenant_id>")
def stripe_webhook(tenant_id: int):
    payload = request.get_json(silent=True) or {}
    event_type = payload.get("type", "unknown")
    if event_type == "payment_intent.succeeded":
        return jsonify({"received": True, "tenant_id": tenant_id}), 200
    return jsonify({"received": True, "ignored": event_type}), 200
