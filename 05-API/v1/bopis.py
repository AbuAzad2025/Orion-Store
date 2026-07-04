from bopis_svc.bopis_service import BopisService
from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin

bopis_bp = Blueprint("bopis", __name__)
_svc = BopisService()


@bopis_bp.route("/locations", methods=["GET"])
def list_locations():
    try:
        require_tenant_admin()
        locations = _svc.list_locations(g.tenant_id)
        return jsonify({"locations": [l.to_dict() for l in locations]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@bopis_bp.route("/locations", methods=["POST"])
def create_location():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        loc = _svc.create_location(
            tenant_id=g.tenant_id,
            code=data["code"],
            name=data["name"],
            address=data.get("address", {}),
            warehouse_id=data.get("warehouse_id"),
        )
        return jsonify({"location": loc.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@bopis_bp.route("/locations/<int:location_id>/slots", methods=["POST"])
def create_slot(location_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        slot = _svc.create_slot(
            location_id=location_id,
            tenant_id=g.tenant_id,
            day_of_week=int(data["day_of_week"]),
            start_time=data["start_time"],
            end_time=data["end_time"],
            max_orders=int(data.get("max_orders", 10)),
        )
        return jsonify({"slot": slot.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
