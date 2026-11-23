"""RMA returns API (wave 9 #63)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import jwt_required

from core.exceptions import OrionError
from core.middleware import require_tenant_admin, require_tenant_context
from core.permissions import require_permission
from core.rate_limit import limiter
from order_svc.order_service import OrderService
from returns.merchandise_return import ReturnItem
from rma_svc.rma_service import RmaService

returns_bp = Blueprint("returns", __name__)
_rma = RmaService()
_orders = OrderService()


_REASON_LABELS = {
    "defective": ("منتج معيب", "Defective product"),
    "wrong_item": ("منتج خاطئ", "Wrong item"),
    "changed_mind": ("تغيير رأي", "Changed mind"),
}


@returns_bp.get("/reasons")
def list_reasons():
    try:
        from core.context import get_locale

        tenant = require_tenant_context()
        reasons = _rma.list_reasons(tenant.id)
        english = get_locale().split("_")[0].lower().startswith("en")
        payload = []
        for reason in reasons:
            data = reason.to_dict()
            labels = _REASON_LABELS.get(data.get("code"))
            if labels:
                data["label"] = labels[1] if english else labels[0]
            payload.append(data)
        return jsonify({"reasons": payload}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@returns_bp.post("/")
@jwt_required()
def create_return():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        order = _orders.get_by_public_id(tenant.id, data["order_public_id"])
        current_user_id = g.user.id if g.user else None
        if (
            order.user_id is not None
            and current_user_id is not None
            and order.user_id != current_user_id
            and not g.is_platform_admin
            and not (g.user and g.user.is_admin)
        ):
            return jsonify({"error": "Order not found."}), 404
        row = _rma.create_return(
            tenant_id=tenant.id,
            order_id=order.id,
            user_id=current_user_id,
            items=data.get("items", []),
            return_type=data.get("return_type", "refund"),
            reason_code=data.get("reason_code"),
            reason_note=data.get("reason_note"),
        )
        items = ReturnItem.query.filter_by(return_id=row.id).all()
        return (
            jsonify(
                {
                    "return": row.to_dict(),
                    "items": [i.to_dict() for i in items],
                }
            ),
            201,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing order_public_id."}), 400


@returns_bp.get("/<int:return_id>")
@jwt_required()
def get_return(return_id: int):
    try:
        tenant = require_tenant_context()
        row = _rma.get_return(tenant.id, return_id)
        current_user_id = g.user.id if g.user else None
        if (
            row.user_id is not None
            and current_user_id is not None
            and row.user_id != current_user_id
            and not g.is_platform_admin
            and not (g.user and g.user.is_admin)
        ):
            return jsonify({"error": "Return not found."}), 404
        items = ReturnItem.query.filter_by(return_id=row.id).all()
        return (
            jsonify(
                {
                    "return": row.to_dict(),
                    "items": [i.to_dict() for i in items],
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@returns_bp.get("/")
def list_returns():
    try:
        require_tenant_admin()
        rows = _rma.list_returns(g.tenant_id)
        return jsonify({"returns": [r.to_dict() for r in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@returns_bp.put("/<int:return_id>/approve")
@limiter.limit("10 per minute")
def approve_return(return_id: int):
    try:
        require_tenant_admin()
        require_permission("tenant.returns.write")
        row = _rma.approve_return(
            tenant_id=g.tenant_id,
            return_id=return_id,
            approved_by=g.user.id if g.user else None,
        )
        return jsonify({"return": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@returns_bp.post("/<int:return_id>/complete")
@limiter.limit("10 per minute")
def complete_return(return_id: int):
    try:
        require_tenant_admin()
        require_permission("tenant.returns.write")
        result = _rma.complete_return(tenant_id=g.tenant_id, return_id=return_id)
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
