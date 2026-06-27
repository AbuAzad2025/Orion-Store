"""RMA returns API (wave 9 #63)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin, require_tenant_context
from order_svc.order_service import OrderService
from returns.merchandise_return import ReturnItem
from rma_svc.rma_service import RmaService

returns_bp = Blueprint("returns", __name__)
_rma = RmaService()
_orders = OrderService()


@returns_bp.get("/reasons")
def list_reasons():
    try:
        tenant = require_tenant_context()
        reasons = _rma.list_reasons(tenant.id)
        return jsonify({"reasons": [r.to_dict() for r in reasons]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@returns_bp.post("/")
def create_return():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        order = _orders.get_by_public_id(tenant.id, data["order_public_id"])
        row = _rma.create_return(
            tenant_id=tenant.id,
            order_id=order.id,
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
def get_return(return_id: int):
    try:
        tenant = require_tenant_context()
        row = _rma.get_return(tenant.id, return_id)
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
def approve_return(return_id: int):
    try:
        require_tenant_admin()
        row = _rma.approve_return(
            tenant_id=g.tenant_id,
            return_id=return_id,
            approved_by=g.user.id if g.user else None,
        )
        return jsonify({"return": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@returns_bp.post("/<int:return_id>/complete")
def complete_return(return_id: int):
    try:
        require_tenant_admin()
        result = _rma.complete_return(tenant_id=g.tenant_id, return_id=return_id)
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
