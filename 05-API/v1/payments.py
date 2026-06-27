"""Payment API (wave 4 #47)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from payment_svc.payment_service import PaymentService

payments_bp = Blueprint("payments", __name__)
_payments = PaymentService()


@payments_bp.post("/orders/<order_public_id>/pay")
def pay_order(order_public_id: str):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        result = _payments.pay_order(
            tenant_id=g.tenant_id,
            order_public_id=order_public_id,
            payment_method=data.get("payment_method", "cod"),
        )
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@payments_bp.post("/<payment_public_id>/refund")
def refund_payment(payment_public_id: str):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        result = _payments.refund(
            tenant_id=g.tenant_id,
            payment_public_id=payment_public_id,
            reason=data.get("reason"),
        )
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
