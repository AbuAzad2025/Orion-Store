from flask import Blueprint, g, jsonify, request

from bundle_svc.bundle_service import BundleService
from core.exceptions import OrionError
from core.middleware import require_tenant_admin

bundles_bp = Blueprint("bundles", __name__)
_svc = BundleService()


@bundles_bp.route("", methods=["GET"])
def list_bundles():
    try:
        require_tenant_admin()
        bundles = _svc.list_bundles(g.tenant_id)
        return jsonify({"bundles": [b.to_dict() for b in bundles]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@bundles_bp.route("", methods=["POST"])
def create_bundle():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        bundle = _svc.create_bundle(
            tenant_id=g.tenant_id,
            name=data["name"],
            slug=data["slug"],
            bundle_price=data["bundle_price"],
        )
        return jsonify({"bundle": bundle.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@bundles_bp.route("/<int:bundle_id>/items", methods=["POST"])
def add_bundle_item(bundle_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        item = _svc.add_item(
            tenant_id=g.tenant_id,
            bundle_id=bundle_id,
            product_id=int(data["product_id"]),
            quantity=int(data.get("quantity", 1)),
            discount_percent=data.get("discount_percent", "0"),
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
