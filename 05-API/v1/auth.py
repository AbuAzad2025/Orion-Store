"""Authentication API (§3.9)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.auth_service import AuthService
from core.exceptions import OrionError

auth_bp = Blueprint("auth", __name__)
_auth = AuthService()


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    tenant_id = data.get("tenant_id")
    try:
        user = _auth.authenticate(email=email, password=password, tenant_id=tenant_id)
        return jsonify({"user": user.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@auth_bp.post("/register/platform")
def register_platform_admin():
    data = request.get_json(silent=True) or {}
    user = _auth.register_super_admin(
        email=data.get("email", "").strip().lower(),
        password=data.get("password", ""),
        first_name=data.get("first_name", "Platform"),
    )
    return jsonify({"user": user.to_dict()}), 201
