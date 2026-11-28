from bundle_svc.bundle_service import BundleService
from flask import Blueprint, g, jsonify, request

from bundle.bundle import ProductBundle
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
            name_en=data.get("name_en"),
            slug=data["slug"],
            bundle_price=data["bundle_price"],
            description=data.get("description"),
            image_url=data.get("image_url"),
            max_per_order=(
                int(data["max_per_order"]) if data.get("max_per_order") else None
            ),
            is_published=bool(data.get("is_published", False)),
        )
        return jsonify({"bundle": bundle.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@bundles_bp.route("/<int:bundle_id>", methods=["PUT"])
def update_bundle(bundle_id: int):
    from orion.extensions import db

    try:
        require_tenant_admin()
        bundle = ProductBundle.query.filter_by(
            id=bundle_id, tenant_id=g.tenant_id
        ).first()
        if not bundle:
            return jsonify({"error": "Bundle not found."}), 404
        data = request.get_json(silent=True) or {}
        for field in (
            "name",
            "name_en",
            "slug",
            "description",
            "image_url",
            "bundle_price",
            "max_per_order",
        ):
            if field in data:
                setattr(bundle, field, data[field])
        if "is_published" in data:
            bundle.is_published = bool(data["is_published"])
        db.session.commit()
        return jsonify({"bundle": bundle.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (ValueError, TypeError):
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


@bundles_bp.route("/<int:bundle_id>/items", methods=["GET"])
def list_bundle_items(bundle_id: int):
    try:
        require_tenant_admin()
        items = _svc.list_items(tenant_id=g.tenant_id, bundle_id=bundle_id)
        return jsonify({"items": [item.to_dict() for item in items]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@bundles_bp.route("/<int:bundle_id>/items/<int:item_id>", methods=["PUT"])
def update_bundle_item(bundle_id: int, item_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        item = _svc.update_item(
            tenant_id=g.tenant_id,
            bundle_id=bundle_id,
            item_id=item_id,
            quantity=data.get("quantity"),
            discount_percent=data.get("discount_percent"),
        )
        return jsonify({"item": item.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@bundles_bp.route("/<int:bundle_id>/items/<int:item_id>", methods=["DELETE"])
def delete_bundle_item(bundle_id: int, item_id: int):
    try:
        require_tenant_admin()
        _svc.delete_item(tenant_id=g.tenant_id, bundle_id=bundle_id, item_id=item_id)
        return jsonify({"deleted": True}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
