"""Storefront customer account API (wave 15)."""

from __future__ import annotations

import uuid

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from auth.auth_service import AuthService
from core.audit_log import audit_log
from core.exceptions import NotFoundError, OrionError
from core.jwt_auth import issue_tokens_for_user
from core.middleware import require_tenant_context
from core.rate_limit import limiter
from order.order import Order
from user.user import User

store_account_bp = Blueprint("store_account", __name__)
_auth = AuthService()


def _current_customer() -> User:
    try:
        public_id = uuid.UUID(get_jwt_identity())
    except (ValueError, TypeError) as exc:
        raise NotFoundError("Customer not found.") from exc
    user = User.query.filter_by(
        public_id=public_id, tenant_id=g.tenant_id, is_customer=True, is_active=True
    ).first()
    if not user:
        raise NotFoundError("Customer not found.")
    return user


@store_account_bp.post("/register")
@limiter.limit("10 per minute")
def register_customer():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        user = _auth.register_tenant_user(
            tenant_id=tenant.id,
            email=data["email"].strip().lower(),
            password=data["password"],
            is_admin=False,
        )
        user.first_name = data.get("first_name")
        user.is_customer = True
        from orion.extensions import db

        db.session.commit()
        audit_log(
            action="customer.register",
            resource_type="user",
            resource_id=user.public_id,
            tenant_id=tenant.id,
        )
        tokens = issue_tokens_for_user(user)
        return jsonify({"user": user.to_dict(), **tokens}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing email or password."}), 400


@store_account_bp.post("/login")
@limiter.limit("20 per minute")
def login_customer():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        user = _auth.authenticate(
            email=data["email"].strip().lower(),
            password=data["password"],
            tenant_id=tenant.id,
        )
        if not user.is_customer:
            return jsonify({"error": "Not a customer account."}), 403
        tokens = issue_tokens_for_user(user)
        return jsonify({"user": user.to_dict(), **tokens}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing email or password."}), 400


@store_account_bp.get("/me")
@jwt_required()
def customer_profile():
    try:
        require_tenant_context()
        user = _current_customer()
        return jsonify({"user": user.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@store_account_bp.get("/orders")
@jwt_required()
def customer_orders():
    try:
        require_tenant_context()
        user = _current_customer()
        rows = (
            Order.query.filter_by(tenant_id=g.tenant_id, customer_email=user.email)
            .order_by(Order.created_at.desc())
            .limit(50)
            .all()
        )
        return jsonify({"orders": [o.to_dict() for o in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
