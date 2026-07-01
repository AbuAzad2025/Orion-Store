from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from schema_markup_svc.schema_markup_service import SchemaMarkupService

schema_markup_bp = Blueprint("schema_markup", __name__)
_svc = SchemaMarkupService()


@schema_markup_bp.route("", methods=["POST"])
def set_markup():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        m = _svc.set_markup(
            tenant_id=tenant.id, product_id=int(data["product_id"]),
            schema_type=data.get("schema_type", "Product"), json_ld=data.get("json_ld", {}),
        )
        return jsonify({"markup": m.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@schema_markup_bp.route("/<int:product_id>", methods=["GET"])
def get_markup(product_id: int):
    try:
        tenant = require_tenant_context()
        m = _svc.get_markup(tenant_id=tenant.id, product_id=product_id)
        if not m:
            return jsonify({"error": "Markup not found."}), 404
        return jsonify({"markup": m.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
