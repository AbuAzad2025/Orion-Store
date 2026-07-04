from flask import Blueprint, g, jsonify, request
from gift.gift_registry import GiftRegistry
from gift_svc.gift_registry_service import GiftRegistryService

from core.exceptions import OrionError
from core.middleware import require_tenant_admin

gift_registries_bp = Blueprint("gift_registries", __name__)
_svc = GiftRegistryService()


@gift_registries_bp.route("", methods=["GET"])
def list_registries():
    try:
        require_tenant_admin()
        registries = GiftRegistry.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"registries": [r.to_dict() for r in registries]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@gift_registries_bp.route("", methods=["POST"])
def create_registry():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        r = _svc.create_registry(
            tenant_id=g.tenant_id,
            customer_email=data["customer_email"],
            registry_name=data["registry_name"],
            event_type=data.get("event_type"),
            event_date=data.get("event_date"),
            is_public=data.get("is_public", True),
        )
        return jsonify({"registry": r.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@gift_registries_bp.route("/<slug>", methods=["GET"])
def get_registry(slug: str):
    try:
        registry = _svc.get_by_slug(slug)
        return jsonify({"registry": registry.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
