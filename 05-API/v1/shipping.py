"""Shipping API (wave 6 #58)."""

from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, g, jsonify, request
from shipping_svc.shipping_service import ShippingService

from core.exceptions import OrionError
from core.middleware import require_tenant_admin, require_tenant_context

shipping_bp = Blueprint("shipping", __name__)
_shipping = ShippingService()


@shipping_bp.get("/methods")
def list_methods():
    try:
        tenant = require_tenant_context()
        methods = _shipping.list_methods(tenant.id)
        return jsonify({"methods": [m.to_dict() for m in methods]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@shipping_bp.post("/methods")
def create_method():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        method = _shipping.create_method(
            tenant_id=g.tenant_id,
            name=data["name"],
            code=data["code"],
            base_cost=data.get("base_cost", "0"),
            free_shipping_threshold=data.get("free_shipping_threshold"),
            is_default=bool(data.get("is_default", False)),
            estimated_days_min=data.get("estimated_days_min"),
            estimated_days_max=data.get("estimated_days_max"),
        )
        _shipping.ensure_default_zone(g.tenant_id)
        return jsonify({"method": method.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing required fields."}), 400


@shipping_bp.post("/calculate")
def calculate_shipping():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        cost = _shipping.calculate_cost(
            tenant_id=tenant.id,
            method_code=data["method_code"],
            subtotal=Decimal(str(data.get("subtotal", "0"))),
            shipping_address=data.get("shipping_address", {}),
            free_shipping=bool(data.get("free_shipping", False)),
        )
        return (
            jsonify(
                {
                    "method_code": data["method_code"],
                    "shipping_cost": str(cost),
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing method_code."}), 400
