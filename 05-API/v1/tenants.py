"""Platform tenant management API."""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from auth.auth_service import AuthService
from core.exceptions import OrionError
from core.middleware import require_platform_admin
from core.pagination import paginate_query, paginated_payload, pagination_params
from core.rate_limit import limiter
from orion.extensions import db
from tenant.tenant import Tenant
from tenant_svc.tenant_service import TenantService

tenant_bp = Blueprint("tenants", __name__)
_tenants = TenantService()
_auth = AuthService()


@tenant_bp.get("/")
def list_tenants():
    try:
        require_platform_admin()
        page, per_page = pagination_params()
        items, meta = paginate_query(
            Tenant.query.filter_by(deleted_at=None).order_by(Tenant.created_at.desc()),
            page,
            per_page,
        )
        return (
            jsonify(paginated_payload("tenants", items, meta, lambda t: t.to_dict())),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_bp.post("/")
@limiter.limit("5 per minute")
def create_tenant():
    try:
        require_platform_admin()
        data = request.get_json(silent=True) or {}
        tenant = _tenants.create_tenant(
            name=data["name"],
            name_en=data.get("name_en"),
            logo_url=data.get("logo_url"),
            slug=data["slug"],
            email=data["email"],
            domain=data.get("domain"),
            status=data.get("status"),
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


@tenant_bp.get("/<int:tenant_id>")
def get_tenant(tenant_id: int):
    try:
        require_platform_admin()
        tenant = Tenant.query.filter_by(id=tenant_id, deleted_at=None).first()
        if not tenant:
            return jsonify({"error": "Tenant not found."}), 404
        return jsonify({"tenant": tenant.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_bp.put("/<int:tenant_id>")
def update_tenant(tenant_id: int):
    try:
        require_platform_admin()
        tenant = Tenant.query.filter_by(id=tenant_id, deleted_at=None).first()
        if not tenant:
            return jsonify({"error": "Tenant not found."}), 404
        data = request.get_json(silent=True) or {}
        previous_status = tenant.status
        status_changed = False
        for field in (
            "name",
            "name_en",
            "logo_url",
            "slug",
            "email",
            "domain",
            "status",
        ):
            if field in data:
                if field == "status":
                    _tenants.validate_status_transition(previous_status, data[field])
                    if data[field] != previous_status:
                        status_changed = True
                        if data[field] == "active":
                            tenant.suspended_until = None
                            tenant.suspended_reason = None
                setattr(tenant, field, data[field])
        if status_changed:
            tenant.version += 1
        db.session.commit()
        if status_changed:
            from core.audit_log import audit_log

            audit_log(
                action="tenant.status_changed",
                resource_type="tenant",
                resource_id=str(tenant.id),
                tenant_id=tenant.id,
                details={"from": previous_status, "to": tenant.status},
            )
        return jsonify({"tenant": tenant.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except Exception:
        current_app.logger.exception("tenant update failed id=%s", tenant_id)
        return jsonify({"error": "Tenant update failed."}), 400


@tenant_bp.delete("/<int:tenant_id>")
def delete_tenant(tenant_id: int):
    try:
        require_platform_admin()
        tenant = Tenant.query.filter_by(id=tenant_id, deleted_at=None).first()
        if not tenant:
            return jsonify({"error": "Tenant not found."}), 404
        tenant.deleted_at = db.func.now()
        db.session.commit()
        return jsonify({"message": "Tenant deleted."}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_bp.post("/<int:tenant_id>/restore")
def restore_tenant(tenant_id: int):
    try:
        require_platform_admin()
        tenant = _tenants.restore(tenant_id)
        return jsonify({"tenant": tenant.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_bp.post("/<int:tenant_id>/reactivate")
def reactivate_tenant(tenant_id: int):
    try:
        require_platform_admin()
        tenant = _tenants.reactivate(tenant_id)
        return jsonify({"tenant": tenant.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@tenant_bp.get("/me")
def current_tenant():
    try:
        if not g.tenant:
            return jsonify({"error": "Tenant context required."}), 404
        data = g.tenant.to_dict()
        if not getattr(g, "user", None):
            for key in (
                "id",
                "public_id",
                "email",
                "domain",
                "custom_domain",
                "status",
                "is_active",
            ):
                data.pop(key, None)
        return jsonify({"tenant": data}), 200
    except OrionError as exc:  # pragma: no cover - to_dict cannot raise
        return jsonify({"error": exc.message}), exc.status_code
