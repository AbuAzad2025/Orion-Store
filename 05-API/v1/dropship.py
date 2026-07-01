from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from dropship_svc.dropship_service import DropshipService

dropship_bp = Blueprint("dropship", __name__)
_svc = DropshipService()


@dropship_bp.route("/pod", methods=["POST"])
def create_pod():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        c = _svc.create_pod_connection(
            tenant_id=tenant.id, provider=data["provider"], api_key=data["api_key"],
            api_url=data.get("api_url"),
        )
        return jsonify({"connection": c.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@dropship_bp.route("/suppliers", methods=["POST"])
def create_supplier():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        s = _svc.create_supplier(
            tenant_id=tenant.id, name=data["name"], contact_email=data["contact_email"],
            fulfillment_time_days=int(data.get("fulfillment_time_days", 0)),
        )
        return jsonify({"supplier": s.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@dropship_bp.route("/orders", methods=["POST"])
def create_dropship_order():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        d = _svc.create_order(
            tenant_id=tenant.id, supplier_id=int(data["supplier_id"]),
            order_id=int(data["order_id"]), cost=data["cost"],
        )
        return jsonify({"dropship_order": d.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
