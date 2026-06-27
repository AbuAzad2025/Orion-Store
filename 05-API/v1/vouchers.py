"""Vouchers API (wave 6 #59)."""

from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin, require_tenant_context
from core.pagination import paginate_query, paginated_payload, pagination_params
from discount_svc.voucher_service import VoucherService

vouchers_bp = Blueprint("vouchers", __name__)
_vouchers = VoucherService()


@vouchers_bp.get("/")
def list_vouchers():
    try:
        require_tenant_admin()
        page, per_page = pagination_params()
        items, meta = paginate_query(
            _vouchers.query_for_tenant(g.tenant_id), page, per_page
        )
        return (
            jsonify(paginated_payload("vouchers", items, meta, lambda v: v.to_dict())),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@vouchers_bp.post("/")
def create_voucher():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        voucher = _vouchers.create(
            tenant_id=g.tenant_id,
            code=data["code"],
            name=data["name"],
            type=data.get("type", "percentage"),
            value=data["value"],
            min_order_value=data.get("min_order_value"),
            max_discount_amount=data.get("max_discount_amount"),
            usage_limit=data.get("usage_limit"),
            is_free_shipping=bool(data.get("is_free_shipping", False)),
        )
        return jsonify({"voucher": voucher.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing required fields."}), 400


@vouchers_bp.get("/<code>/validate")
def validate_voucher(code: str):
    try:
        tenant = require_tenant_context()
        subtotal = Decimal(str(request.args.get("subtotal", "0")))
        preview = _vouchers.validate(tenant.id, code, subtotal)
        return jsonify({"voucher": preview.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@vouchers_bp.post("/<code>/apply")
def apply_voucher(code: str):
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        subtotal = Decimal(str(data.get("subtotal", "0")))
        preview = _vouchers.validate(tenant.id, code, subtotal)
        return jsonify({"applied": preview.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
