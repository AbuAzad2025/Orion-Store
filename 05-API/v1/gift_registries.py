from flask import Blueprint, g, jsonify, request
from gift.gift_registry import GiftRegistry
from gift_svc.gift_registry_service import GiftRegistryService

from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    OrionError,
)
from core.middleware import require_tenant_admin, require_tenant_context

gift_registries_bp = Blueprint("gift_registries", __name__)
_svc = GiftRegistryService()


def _member_registry(slug: str) -> GiftRegistry:
    """Allow store staff or the registry owner; deny everyone else."""
    tenant = require_tenant_context()
    registry = GiftRegistry.query.filter_by(slug=slug, tenant_id=tenant.id).first()
    if not registry:
        raise NotFoundError("Registry not found.")
    user = getattr(g, "user", None)
    if user is None:
        raise AuthenticationError("Authentication required.")
    is_store = bool(
        getattr(g, "is_platform_admin", False)
        or (user.is_admin and user.tenant_id == tenant.id)
    )
    is_owner = (
        registry.user_id is not None and registry.user_id == user.id
    ) or registry.customer_email.lower() == (user.email or "").lower()
    if not is_store and not is_owner:
        raise AuthorizationError("Permission denied.")
    return registry


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
            user_id=getattr(g.user, "id", None) if g.user else None,
        )
        return jsonify({"registry": r.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@gift_registries_bp.route("/<slug>", methods=["GET"])
def get_registry(slug: str):
    try:
        tenant = require_tenant_context()
        registry = _svc.get_by_slug(slug, tenant.id)
        data = registry.to_dict()
        data.pop("customer_email", None)
        data.pop("user_id", None)
        return jsonify({"registry": data}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@gift_registries_bp.route("/<slug>/items", methods=["POST"])
def add_registry_item(slug: str):
    try:
        registry = _member_registry(slug)
        data = request.get_json(silent=True) or {}
        item = _svc.add_item(
            tenant_id=g.tenant_id,
            registry_id=registry.id,
            product_id=int(data["product_id"]),
            quantity=int(data.get("quantity", 1)),
        )
        return jsonify({"item": item.to_dict(), "registry": registry.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@gift_registries_bp.route("/<slug>/items", methods=["GET"])
def list_registry_items(slug: str):
    try:
        registry = _member_registry(slug)
        items = _svc.list_items(registry_id=registry.id)
        return (
            jsonify(
                {
                    "registry": registry.to_dict(),
                    "items": [item.to_dict() for item in items],
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
