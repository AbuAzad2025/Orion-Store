"""Brands API — tenant-scoped list/create (feeds product forms)."""

from __future__ import annotations

import uuid

from catalog.brand import Brand
from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from orion.extensions import db

brands_bp = Blueprint("brands", __name__)


@brands_bp.get("/")
def list_brands():
    try:
        require_tenant_admin()
        brands = (
            Brand.query.filter_by(tenant_id=g.tenant_id)
            .order_by(Brand.name)
            .all()
        )
        return jsonify({"brands": [b.to_dict() for b in brands]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@brands_bp.post("/")
def create_brand():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify({"error": "Missing name."}), 400
        slug = str(data.get("slug") or name.lower().replace(" ", "-"))
        if Brand.query.filter_by(tenant_id=g.tenant_id, slug=slug).first():
            return jsonify({"error": "Brand slug already exists."}), 400
        brand = Brand(tenant_id=g.tenant_id, name=name, slug=slug)
        db.session.add(brand)
        db.session.commit()
        return jsonify({"brand": brand.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
