"""Platform user management API."""

from __future__ import annotations

import uuid

from flask import Blueprint, jsonify, request

from auth.auth_service import AuthService
from core.exceptions import OrionError
from core.middleware import require_platform_admin
from core.pagination import paginate_query, paginated_payload, pagination_params
from orion.extensions import db
from user.role import Role
from user.user import User

users_bp = Blueprint("users", __name__)
_auth = AuthService()


@users_bp.get("/")
def list_users():
    try:
        require_platform_admin()
        page, per_page = pagination_params()
        query = User.query.filter(User.deleted_at.is_(None)).order_by(
            User.created_at.desc()
        )
        items, meta = paginate_query(query, page, per_page)
        return (
            jsonify(paginated_payload("users", items, meta, lambda u: u.to_dict())),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@users_bp.post("/")
def create_user():
    try:
        require_platform_admin()
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        tenant_id = data.get("tenant_id")
        is_admin = data.get("is_admin", True)
        is_superuser = data.get("is_superuser", False)

        if not email or not password:
            return jsonify({"error": "Email and password required."}), 400

        if is_superuser:
            user = _auth.register_super_admin(email=email, password=password)
        else:
            if not tenant_id:
                return jsonify({"error": "tenant_id required for tenant user."}), 400
            user = _auth.register_tenant_user(
                tenant_id=tenant_id,
                email=email,
                password=password,
                is_admin=is_admin,
            )
        return jsonify({"user": user.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@users_bp.put("/<int:user_id>")
def update_user(user_id: int):
    try:
        require_platform_admin()
        user = User.query.filter_by(id=user_id, deleted_at=None).first()
        if not user:
            return jsonify({"error": "User not found."}), 404
        data = request.get_json(silent=True) or {}
        for field in ("first_name", "last_name", "is_admin", "is_staff", "is_active"):
            if field in data:
                setattr(user, field, data[field])
        db.session.commit()
        return jsonify({"user": user.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@users_bp.delete("/<int:user_id>")
def delete_user(user_id: int):
    try:
        require_platform_admin()
        user = User.query.filter_by(id=user_id, deleted_at=None).first()
        if not user:
            return jsonify({"error": "User not found."}), 404
        user.deleted_at = db.func.now()
        db.session.commit()
        return jsonify({"message": "User deleted."}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@users_bp.post("/<public_id>/roles")
def assign_user_role(public_id: str):
    """Assign a tenant role to a user (platform admins only).

    ``tenant_id`` in the body is validated against both the target user and
    the role. When omitted, the user's own tenant is used.
    """
    try:
        require_platform_admin()
        try:
            uid = uuid.UUID(public_id)
        except (ValueError, TypeError, AttributeError):
            return jsonify({"error": "Invalid public_id."}), 400
        user = User.query.filter_by(public_id=uid, deleted_at=None).first()
        if not user:
            return jsonify({"error": "User not found."}), 404

        data = request.get_json(silent=True) or {}
        role_code = str(data.get("role_code") or "").strip()
        if not role_code:
            return jsonify({"error": "role_code required."}), 400

        tenant_id = data.get("tenant_id")
        if tenant_id is not None:
            try:
                tenant_id = int(tenant_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid tenant_id."}), 400

        assignment = _auth.assign_role(
            tenant_id=tenant_id if tenant_id is not None else user.tenant_id,
            user_id=user.id,
            role_code=role_code,
        )
        role = db.session.get(Role, assignment.role_id)
        return (
            jsonify(
                {
                    "user_role": assignment.to_dict(),
                    "role": role.to_dict() if role else None,
                }
            ),
            201,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
