"""Impersonation service (AZ-0.18)."""

from __future__ import annotations

from datetime import timedelta

from flask import g, request

from core.exceptions import AuthorizationError, NotFoundError, ValidationError
from core.utils import utc_now
from orion.extensions import db
from platform_models.audit_log import AuditLog
from platform_models.impersonation_session import ImpersonationSession
from user.user import User

MAX_IMPERSONATION_DURATION = timedelta(hours=4)
ALLOWED_IMPERSONATION_ACTIONS = (
    "impersonation_start",
    "impersonation_end",
    "impersonation_revoked",
)


class ImpersonationService:
    def start(
        self,
        *,
        impersonator_user_id: int,
        target_user_id: int,
        tenant_id: int,
        duration: timedelta = MAX_IMPERSONATION_DURATION,
    ) -> ImpersonationSession:
        impersonator = User.query.filter_by(
            id=impersonator_user_id, is_active=True
        ).first()
        if not impersonator or not impersonator.is_superuser:
            raise AuthorizationError("Only platform admins can start impersonation.")

        target = User.query.filter_by(
            id=target_user_id, tenant_id=tenant_id, is_active=True
        ).first()
        if not target:
            raise NotFoundError("Target user not found in this tenant.")
        if target.is_superuser:
            raise AuthorizationError("Cannot impersonate a platform admin.")

        active = (
            ImpersonationSession.query.filter_by(
                impersonator_user_id=impersonator_user_id, revoked=False, ended_at=None
            )
            .filter(ImpersonationSession.expires_at > utc_now())
            .first()
        )
        if active:
            raise ValidationError(
                "Impersonation already active. End current session first."
            )

        started = utc_now()
        expires = started + duration

        session = ImpersonationSession(
            impersonator_user_id=impersonator_user_id,
            target_user_id=target_user_id,
            tenant_id=tenant_id,
            started_at=started,
            expires_at=expires,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.remote_addr,
        )
        db.session.add(session)

        audit = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=impersonator_user_id,
            action="impersonation_start",
            resource_type="user",
            resource_id=str(target_user_id),
            details={
                "target_email": target.email,
                "expires_at": expires.isoformat(),
                "impersonator_user_id": impersonator_user_id,
            },
        )
        db.session.add(audit)
        db.session.commit()
        return session

    def end(
        self, *, impersonator_user_id: int, session_id: int
    ) -> ImpersonationSession:
        session = ImpersonationSession.query.filter_by(
            id=session_id, impersonator_user_id=impersonator_user_id
        ).first()
        if not session:
            raise NotFoundError("Impersonation session not found.")
        if session.ended_at or session.revoked:
            raise ValidationError("Session already ended.")

        session.ended_at = utc_now()
        session.revoked = True

        audit = AuditLog(
            tenant_id=session.tenant_id,
            actor_user_id=session.target_user_id,
            action="impersonation_end",
            resource_type="user",
            resource_id=str(session.target_user_id),
            details={
                "session_id": session.id,
                "impersonator_user_id": impersonator_user_id,
            },
        )
        db.session.add(audit)
        db.session.commit()
        return session

    def revoke_all(self, *, impersonator_user_id: int) -> int:
        active = (
            ImpersonationSession.query.filter_by(
                impersonator_user_id=impersonator_user_id, revoked=False, ended_at=None
            )
            .filter(ImpersonationSession.expires_at > utc_now())
            .all()
        )
        count = 0
        for s in active:
            s.ended_at = utc_now()
            s.revoked = True
            audit = AuditLog(
                tenant_id=s.tenant_id,
                actor_user_id=s.target_user_id,
                action="impersonation_revoked",
                resource_type="user",
                resource_id=str(s.target_user_id),
                details={
                    "session_id": s.id,
                    "impersonator_user_id": impersonator_user_id,
                },
            )
            db.session.add(audit)
            count += 1
        db.session.commit()
        return count

    def get_active(self, *, impersonator_user_id: int) -> ImpersonationSession | None:
        return (
            ImpersonationSession.query.filter_by(
                impersonator_user_id=impersonator_user_id, revoked=False, ended_at=None
            )
            .filter(ImpersonationSession.expires_at > utc_now())
            .first()
        )

    def validate_session(
        self, *, impersonator_user_id: int, target_user_id: int, tenant_id: int
    ) -> ImpersonationSession:
        session = (
            ImpersonationSession.query.filter_by(
                impersonator_user_id=impersonator_user_id,
                target_user_id=target_user_id,
                tenant_id=tenant_id,
                revoked=False,
                ended_at=None,
            )
            .filter(ImpersonationSession.expires_at > utc_now())
            .first()
        )
        if not session:
            raise AuthorizationError("No valid impersonation session.")
        return session
