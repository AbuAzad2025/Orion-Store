from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from metafield_svc.metafield_service import MetafieldService

metafields_bp = Blueprint("metafields", __name__)
_svc = MetafieldService()


@metafields_bp.route("/definitions", methods=["POST"])
def define():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        defn = _svc.define(
            tenant_id=tenant.id, owner_type=data["owner_type"], key=data["key"],
            label=data["label"], field_type=data.get("field_type", "string"),
            is_required=data.get("is_required", False),
        )
        return jsonify({"definition": defn.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@metafields_bp.route("/values", methods=["POST"])
def set_value():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        mf = _svc.set_value(
            tenant_id=tenant.id, definition_id=int(data["definition_id"]),
            owner_id=int(data["owner_id"]), value=data.get("value"),
            json_value=data.get("json_value"),
        )
        return jsonify({"metafield": mf.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@metafields_bp.route("/<owner_type>/<int:owner_id>", methods=["GET"])
def get_for_owner(owner_type: str, owner_id: int):
    try:
        tenant = require_tenant_context()
        values = _svc.get_for_owner(tenant_id=tenant.id, owner_type=owner_type, owner_id=owner_id)
        return jsonify({"metafields": values}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
