"""Platform Admin Impersonation API (AZ-0.18)."""

from __future__ import annotations

from datetime import timedelta

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_access_cookies,
    unset_refresh_cookies,
)

from core.jwt_auth import issue_tokens_for_user, revoke_current_tokens
from core.middleware import require_platform_admin
from core.rate_limit import limiter
from core.utils import utc_now
from orion.extensions import db
from platform_models.impersonation_session import ImpersonationSession
from user.user import User

impersonation_bp = Blueprint(
    "impersonation", __name__, url_prefix="/platform/impersonation"
)

MAX_IMPERSONATION_DURATION = timedelta(hours=4)


@impersonation_bp.post("/start")
@jwt_required()
@limiter.limit("5 per minute")
def start_impersonation():
    """Start impersonating a tenant admin.

    Body: { "target_user_id": <int>, "duration_hours": <int, optional> }
    Returns impersonation JWT cookies + session info.
    """
    require_platform_admin()
    data = request.get_json(silent=True) or {}
    target_user_id = data.get("target_user_id")
    if not target_user_id or not isinstance(target_user_id, int):
        return jsonify({"error": "target_user_id (int) is required"}), 400

    duration_hours = data.get("duration_hours")
    if duration_hours is not None:
        if (
            not isinstance(duration_hours, int)
            or duration_hours < 1
            or duration_hours > 4
        ):
            return jsonify({"error": "duration_hours must be 1-4"}), 400
        duration = timedelta(hours=duration_hours)
    else:
        duration = MAX_IMPERSONATION_DURATION

    impersonator_id = g.user.id
    target = User.query.filter_by(id=target_user_id, is_active=True).first()
    if not target:
        return jsonify({"error": "Target user not found"}), 404
    if target.is_superuser:
        return jsonify({"error": "Cannot impersonate a platform admin"}), 403
    if not target.is_admin:
        return jsonify({"error": "Can only impersonate tenant admins"}), 403
    if not target.tenant_id:
        return jsonify({"error": "Target user has no tenant"}), 400

    active = (
        ImpersonationSession.query.filter_by(
            impersonator_user_id=impersonator_id, revoked=False, ended_at=None
        )
        .filter(ImpersonationSession.expires_at > db.func.now())
        .first()
    )
    if active:
        return (
            jsonify(
                {"error": "Impersonation already active. End current session first."}
            ),
            409,
        )

    started = utc_now()
    expires = started + duration
    session = ImpersonationSession(
        impersonator_user_id=impersonator_id,
        target_user_id=target_user_id,
        tenant_id=target.tenant_id,
        started_at=started,
        expires_at=expires,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.remote_addr,
    )
    db.session.add(session)

    from core.audit_log import audit_log

    audit_log(
        action="impersonation_start",
        resource_type="user",
        resource_id=str(target_user_id),
        tenant_id=target.tenant_id,
        details={"target_email": target.email, "expires_at": expires.isoformat()},
    )
    db.session.commit()

    tokens = {
        "access_token": create_access_token(
            identity=str(target.public_id),
            additional_claims={
                "is_superuser": target.is_superuser,
                "tenant_id": target.tenant_id,
                "impersonation": {
                    "impersonator_user_id": impersonator_id,
                    "impersonator_public_id": str(g.user.public_id),
                    "target_user_id": target.id,
                    "target_public_id": str(target.public_id),
                },
            },
            expires_delta=duration,
        ),
        "refresh_token": create_refresh_token(
            identity=str(target.public_id),
            additional_claims={
                "is_superuser": target.is_superuser,
                "tenant_id": target.tenant_id,
                "impersonation": {
                    "impersonator_user_id": impersonator_id,
                    "impersonator_public_id": str(g.user.public_id),
                    "target_user_id": target.id,
                    "target_public_id": str(target.public_id),
                },
            },
            expires_delta=duration,
        ),
    }

    response = jsonify(
        {
            "session": session.to_dict(),
            "target_user": target.to_dict(),
        }
    )
    set_access_cookies(response, tokens["access_token"])
    set_refresh_cookies(response, tokens["refresh_token"])
    return response, 200


@impersonation_bp.post("/end")
@jwt_required()
def end_impersonation():
    """End the current impersonation session and restore platform admin cookies."""
    claims = get_jwt()
    impersonation = claims.get("impersonation")
    if impersonation:
        impersonator_id = impersonation.get("impersonator_user_id")
        target_user_id = impersonation.get("target_user_id")
        if impersonator_id and target_user_id:
            session = (
                ImpersonationSession.query.filter_by(
                    impersonator_user_id=impersonator_id,
                    target_user_id=target_user_id,
                )
                .order_by(ImpersonationSession.id.desc())
                .first()
            )
            if session and session.is_active():
                # The impersonation token belongs to the TARGET admin. It may
                # end its own session, but must never mint platform tokens or
                # revoke somebody else's session.
                if not g.user or g.user.id != target_user_id:
                    return jsonify({"error": "Unauthorized"}), 403
                session.ended_at = utc_now()
                session.revoked = True
                from core.audit_log import audit_log

                audit_log(
                    action="impersonation_end",
                    resource_type="user",
                    resource_id=str(session.target_user_id),
                    tenant_id=session.tenant_id,
                    details={"session_id": session.id, "actor_user_id": g.user.id},
                )
                revoke_current_tokens()
                response = jsonify(
                    {
                        "message": (
                            "Impersonation ended. Sign in again to restore "
                            "platform access."
                        ),
                        "session": session.to_dict(),
                    }
                )
                unset_access_cookies(response)
                unset_refresh_cookies(response)
                return response, 200
                return (
                    jsonify({"active": False, "reason": "Session expired or revoked"}),
                    200,
                )

    if g.is_platform_admin and g.user:
        session = (
            ImpersonationSession.query.filter_by(
                impersonator_user_id=g.user.id, revoked=False, ended_at=None
            )
            .filter(ImpersonationSession.expires_at > db.func.now())
            .first()
        )
        if not session:
            return jsonify({"active": False, "session": None}), 200
        session.ended_at = utc_now()
        session.revoked = True
        from core.audit_log import audit_log

        audit_log(
            action="impersonation_end",
            resource_type="user",
            resource_id=str(session.target_user_id),
            tenant_id=session.tenant_id,
            details={"session_id": session.id, "actor_user_id": g.user.id},
        )
        db.session.commit()
        revoke_current_tokens()
        tokens = issue_tokens_for_user(g.user)
        response = jsonify(
            {"message": "Impersonation ended", "session": session.to_dict()}
        )
        set_access_cookies(response, tokens["access_token"])
        set_refresh_cookies(response, tokens["refresh_token"])
        return response, 200

    return jsonify({"active": False, "session": None, "reason": "Unauthorized"}), 401


@impersonation_bp.get("/status")
@jwt_required()
def impersonation_status():
    """Return whether the current admin has an active impersonation session."""
    claims = get_jwt()
    impersonation = claims.get("impersonation")
    if impersonation:
        impersonator_id = impersonation.get("impersonator_user_id")
        target_user_id = impersonation.get("target_user_id")
        if impersonator_id and target_user_id:
            session = (
                ImpersonationSession.query.filter_by(
                    impersonator_user_id=impersonator_id,
                    target_user_id=target_user_id,
                )
                .order_by(ImpersonationSession.id.desc())
                .first()
            )
            if session:
                return (
                    jsonify(
                        {"active": session.is_active(), "session": session.to_dict()}
                    ),
                    200,
                )
            return jsonify({"active": False, "session": None}), 200

    if g.get("user") and getattr(g.user, "is_superuser", False):
        session = (
            ImpersonationSession.query.filter_by(
                impersonator_user_id=g.user.id, revoked=False, ended_at=None
            )
            .filter(ImpersonationSession.expires_at > db.func.now())
            .first()
        )
        if not session:
            return jsonify({"active": False, "session": None}), 200
        return (
            jsonify({"active": session.is_active(), "session": session.to_dict()}),
            200,
        )

    return jsonify({"active": False, "session": None}), 200
