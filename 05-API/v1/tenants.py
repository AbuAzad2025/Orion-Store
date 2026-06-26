"""Platform tenant management API."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from auth.auth_service import AuthService
from core.exceptions import OrionError
from core.middleware import require_platform_admin
from tenant_svc.tenant_service import TenantService

tenant_bp = Blueprint("tenants", __name__)
_tenants = TenantService()
_auth = AuthService()


@tenant_bp.get("/")
def list_tenants():
    try:
        require_platform_admin()
        items = [_t.to_dict() for _t in _tenants.list_tenants()]
        return jsonify({"tenants": items}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_bp.post("/")
def create_tenant():
    try:
        require_platform_admin()
        data = request.get_json(silent=True) or {}
        tenant = _tenants.create_tenant(
            name=data["name"],
            slug=data["slug"],
            email=data["email"],
            domain=data.get("domain"),
        )
        if data.get("admin_email") and data.get("admin_password"):
            _auth.register_tenant_user(
                tenant_id=tenant.id,
                email=data["admin_email"],
                password=data["admin_password"],
                is_admin=True,
            )
        return jsonify({"tenant": tenant.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing required fields."}), 400


@tenant_bp.get("/me")
def current_tenant():
    try:
        if not g.tenant:
            return jsonify({"error": "Tenant context required."}), 404
        return jsonify({"tenant": g.tenant.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
