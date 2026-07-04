"""Platform user management API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.auth_service import AuthService
from core.exceptions import OrionError
from core.middleware import require_platform_admin
from core.pagination import paginate_query, paginated_payload, pagination_params
from orion.extensions import db
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
