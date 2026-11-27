"""Storefront customer account API (wave 15)."""

from __future__ import annotations

import uuid

from flask import Blueprint, g, jsonify, request, session
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
)
from sqlalchemy import and_, or_

from auth.auth_service import AuthService
from core.audit_log import audit_log
from core.exceptions import AuthenticationError, NotFoundError, OrionError
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
        raise AuthenticationError("Customer not found.") from exc
    user = User.query.filter_by(
        public_id=public_id, tenant_id=g.tenant_id, is_customer=True, is_active=True
    ).first()
    if not user:
        raise AuthenticationError("Customer not found.")
    return user


@store_account_bp.post("/register")
@limiter.limit("5 per minute")
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
        response = jsonify({"user": user.to_dict(), **tokens})
        set_access_cookies(response, tokens["access_token"])
        set_refresh_cookies(response, tokens["refresh_token"])
        return response, 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing email or password."}), 400


@store_account_bp.post("/login")
@limiter.limit("10 per minute")
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
        response = jsonify({"user": user.to_dict(), **tokens})
        set_access_cookies(response, tokens["access_token"])
        set_refresh_cookies(response, tokens["refresh_token"])
        return response, 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing email or password."}), 400


@store_account_bp.post("/logout")
@jwt_required()
@limiter.limit("10 per minute")
def customer_logout():
    from flask_jwt_extended import unset_jwt_cookies

    from core.jwt_auth import revoke_current_tokens

    revoke_current_tokens()
    session.clear()
    response = jsonify({"ok": True})
    unset_jwt_cookies(response)
    return response, 200


@store_account_bp.post("/data-requests")
@jwt_required()
@limiter.limit("5 per minute")
def create_own_data_request():
    """A logged-in customer files their own GDPR export/delete request."""
    from compliance_svc.compliance_service import ComplianceService

    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        request_type = str(data.get("request_type", "")).strip().lower()
        if request_type not in ("export", "delete"):
            return jsonify({"error": "request_type must be export or delete."}), 400
        req = ComplianceService().create_data_request(
            tenant_id=tenant.id,
            customer_email=g.user.email,
            request_type=request_type,
        )
        return jsonify({"request": req.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@store_account_bp.get("/data-requests/<int:request_id>/export")
@jwt_required()
@limiter.limit("10 per minute")
def export_own_data(request_id: int):
    from compliance_svc.compliance_service import ComplianceService

    try:
        tenant = require_tenant_context()
        req = ComplianceService().get_data_request(
            tenant_id=tenant.id, request_id=request_id
        )
        if req.customer_email.lower() != g.user.email.lower():
            return jsonify({"error": "Permission denied."}), 403
        return (
            jsonify(
                ComplianceService().export_subject_data(
                    tenant_id=tenant.id, request_id=request_id
                )
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@store_account_bp.post("/data-requests/<int:request_id>/delete")
@jwt_required()
@limiter.limit("5 per minute")
def delete_own_data(request_id: int):
    from compliance_svc.compliance_service import ComplianceService

    try:
        tenant = require_tenant_context()
        req = ComplianceService().get_data_request(
            tenant_id=tenant.id, request_id=request_id
        )
        if req.customer_email.lower() != g.user.email.lower():
            return jsonify({"error": "Permission denied."}), 403
        if req.request_type != "delete":
            return jsonify({"error": "Request is not a deletion request."}), 400
        return (
            jsonify(
                ComplianceService().execute_subject_deletion(
                    tenant_id=tenant.id, request_id=request_id
                )
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


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
        # New orders are tied to the account id; legacy guest orders are still
        # matched by email so existing customers do not lose their history.
        rows = (
            Order.query.filter(
                Order.tenant_id == g.tenant_id,
                or_(
                    Order.user_id == user.id,
                    and_(
                        Order.user_id.is_(None),
                        Order.customer_email == user.email,
                    ),
                ),
            )
            .order_by(Order.created_at.desc())
            .limit(50)
            .all()
        )
        return jsonify({"orders": [o.to_dict() for o in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
