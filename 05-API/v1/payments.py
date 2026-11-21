"""Payment API (wave 4 #47)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError, ValidationError
from core.middleware import require_tenant_admin
from core.permissions import require_permission
from core.rate_limit import limiter
from payment_svc.payment_service import PaymentService

payments_bp = Blueprint("payments", __name__)
_payments = PaymentService()


@payments_bp.post("/orders/<order_public_id>/pay")
@limiter.limit("10 per minute")
def pay_order(order_public_id: str):
    try:
        require_tenant_admin()
        require_permission("tenant.payments.write")
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
@limiter.limit("10 per minute")
def refund_payment(payment_public_id: str):
    try:
        require_tenant_admin()
        require_permission("tenant.payments.write")
        data = request.get_json(silent=True) or {}
        raw_amount = data.get("amount")
        amount = None
        if raw_amount is not None:
            try:
                amount = Decimal(str(raw_amount))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ValidationError("Invalid refund amount.") from exc
        result = _payments.refund(
            tenant_id=g.tenant_id,
            payment_public_id=payment_public_id,
            amount=amount,
            reason=data.get("reason"),
        )
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
