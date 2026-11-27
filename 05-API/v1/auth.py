"""Authentication API (§3.9)."""

from __future__ import annotations

from compliance_svc.compliance_service import ComplianceService
from flask import Blueprint, g, jsonify, request, session
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
)

from auth.auth_service import AuthService
from core.exceptions import OrionError
from core.jwt_auth import issue_tokens_for_user
from core.rate_limit import limiter

auth_bp = Blueprint("auth", __name__)
_auth = AuthService()
_compliance = ComplianceService()


def _resolve_tenant_id(tenant_ref: str | int | None) -> int | None:
    if tenant_ref is None:
        return None
    if isinstance(tenant_ref, int):
        return tenant_ref
    from tenant.tenant import Tenant

    tenant = Tenant.query.filter_by(slug=str(tenant_ref)).first()
    return tenant.id if tenant else None


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    tenant_ref = data.get("tenant_id")
    tenant_id = _resolve_tenant_id(tenant_ref)
    try:
        user = _auth.authenticate(email=email, password=password, tenant_id=tenant_id)
        tokens = issue_tokens_for_user(user)
        response = jsonify({"user": user.to_dict(), **tokens})
        set_access_cookies(response, tokens["access_token"])
        set_refresh_cookies(response, tokens["refresh_token"])
        return response, 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
@limiter.limit("5 per minute")
def refresh():
    identity = get_jwt_identity()
    claims = get_jwt()
    additional = {
        key: claims[key]
        for key in ("is_superuser", "tenant_id", "impersonation")
        if key in claims
    }
    # The impersonation grant is deliberately preserved: middleware validates
    # the underlying session on every request (including refresh), so a stale
    # refresh token cannot mint a clean tenant-admin token after revocation.
    token = create_access_token(identity=identity, additional_claims=additional)
    response = jsonify({"access_token": token})
    set_access_cookies(response, token)
    return response, 200


@auth_bp.post("/logout")
@jwt_required()
@limiter.limit("10 per minute")
def logout():
    """Invalidate the access and refresh tokens server-side, then clear cookies."""
    from flask_jwt_extended import unset_access_cookies, unset_refresh_cookies

    from core.jwt_auth import revoke_current_tokens

    revoke_current_tokens()
    session.clear()
    response = jsonify({"message": "Logged out."})
    unset_access_cookies(response)
    unset_refresh_cookies(response)
    return response, 200


@auth_bp.post("/register/platform")
def register_platform_admin():
    """Public platform-admin registration is permanently disabled.

    Platform administrators must be created through the secure CLI bootstrap
    script (``scripts/bootstrap_cli.py``) or by an existing platform administrator
    through authenticated internal services.

    This endpoint exists only for backward compatibility and always rejects
    requests. No configuration flag can re-enable it.
    """
    return (
        jsonify(
            {
                "error": "Platform admin registration is not available through this endpoint."
            }
        ),
        404,
    )


@auth_bp.post("/sso/exchange")
@limiter.limit("10 per minute")
def sso_exchange():
    """Exchange a validated SSO provider code for the usual JWT token pair."""
    data = request.get_json(silent=True) or {}
    tenant_id = g.tenant_id
    if not tenant_id:
        return jsonify({"error": "Tenant context required."}), 400
    try:
        user = _compliance.exchange_sso_code(
            tenant_id=tenant_id,
            provider_code=data.get("provider_code") or data.get("token"),
            external_email=data.get("external_email"),
            provider_type=data.get("provider_type"),
            client_id=data.get("client_id"),
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):  # pragma: no cover - dead handler
        return jsonify({"error": "Invalid request."}), 400

    tokens = issue_tokens_for_user(user)
    response = jsonify({"user": user.to_dict(), **tokens})
    set_access_cookies(response, tokens["access_token"])
    set_refresh_cookies(response, tokens["refresh_token"])
    return response, 200
