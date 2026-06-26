"""Category API (wave 2 #24)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from catalog_svc.category_service import CategoryService
from core.exceptions import OrionError
from core.middleware import require_tenant_admin

categories_bp = Blueprint("categories", __name__)
_categories = CategoryService()


@categories_bp.get("/")
def list_categories():
    try:
        require_tenant_admin()
        items = [_c.to_dict() for _c in _categories.list_for_tenant(g.tenant_id)]
        return jsonify({"categories": items}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@categories_bp.post("/")
def create_category():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        category = _categories.create(
            tenant_id=g.tenant_id,
            name=data["name"],
            slug=data["slug"],
            parent_id=data.get("parent_id"),
        )
        return jsonify({"category": category.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing required fields."}), 400
