"""Authentication API (§3.9)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from auth.auth_service import AuthService
from core.exceptions import OrionError
from core.jwt_auth import issue_tokens_for_user

auth_bp = Blueprint("auth", __name__)
_auth = AuthService()


def _resolve_tenant_id(tenant_ref: str | int | None) -> int | None:
    if tenant_ref is None:
        return None
    if isinstance(tenant_ref, int):
        return tenant_ref
    from tenant.tenant import Tenant

    tenant = Tenant.query.filter_by(slug=str(tenant_ref)).first()
    return tenant.id if tenant else None


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    tenant_ref = data.get("tenant_id")
    tenant_id = _resolve_tenant_id(tenant_ref)
    try:
        user = _auth.authenticate(email=email, password=password, tenant_id=tenant_id)
        tokens = issue_tokens_for_user(user)
        return jsonify({"user": user.to_dict(), **tokens}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=identity)}), 200


@auth_bp.post("/register/platform")
def register_platform_admin():
    data = request.get_json(silent=True) or {}
    user = _auth.register_super_admin(
        email=data.get("email", "").strip().lower(),
        password=data.get("password", ""),
        first_name=data.get("first_name", "Platform"),
    )
    return jsonify({"user": user.to_dict()}), 201
