"""Product API — tenant admin CRUD (wave 2 #24)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from catalog_svc.product_service import ProductService
from core.exceptions import OrionError
from core.middleware import require_tenant_admin

products_bp = Blueprint("products", __name__)
_products = ProductService()


@products_bp.get("/")
def list_products():
    try:
        require_tenant_admin()
        items = [_p.to_dict() for _p in _products.list_for_tenant(g.tenant_id)]
        return jsonify({"products": items}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@products_bp.post("/")
def create_product():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        product = _products.create(
            tenant_id=g.tenant_id,
            name=data["name"],
            slug=data["slug"],
            price=data["price"],
            sku=data.get("sku"),
            quantity=int(data.get("quantity", 0)),
            category_id=data.get("category_id"),
            brand_id=data.get("brand_id"),
            is_published=bool(data.get("is_published", False)),
        )
        return jsonify({"product": product.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing required fields."}), 400


@products_bp.get("/<public_id>")
def get_product(public_id: str):
    try:
        require_tenant_admin()
        product = _products.get_by_public_id(g.tenant_id, public_id)
        return jsonify({"product": product.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@products_bp.put("/<public_id>")
def update_product(public_id: str):
    try:
        require_tenant_admin()
        product = _products.get_by_public_id(g.tenant_id, public_id)
        data = request.get_json(silent=True) or {}
        allowed = {
            k: data[k]
            for k in (
                "name",
                "slug",
                "price",
                "sku",
                "quantity",
                "category_id",
                "brand_id",
                "is_published",
                "is_featured",
            )
            if k in data
        }
        product = _products.update(product, **allowed)
        return jsonify({"product": product.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@products_bp.delete("/<public_id>")
def delete_product(public_id: str):
    try:
        require_tenant_admin()
        product = _products.get_by_public_id(g.tenant_id, public_id)
        _products.soft_delete(product)
        return jsonify({"deleted": True}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
