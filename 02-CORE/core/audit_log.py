"""Sensitive action audit trail (§0.13.4).

The actor is *always* resolved from the authenticated Flask context.  This
module deliberately has no ``user_id`` / ``generated_by`` parameter, so a
caller (and therefore an HTTP client) cannot attribute an action to anyone
other than the current user.
"""

from __future__ import annotations

from flask import g, has_app_context

from orion.extensions import db
from platform_models.audit_log import AuditLog


def _current_actor_id() -> int | None:
    """Return the authenticated user id, or ``None`` outside a Flask context."""
    if not has_app_context():
        return None
    return getattr(getattr(g, "user", None), "id", None)


def _current_tenant_id() -> int | None:
    if not has_app_context():
        return None
    return getattr(g, "tenant_id", None)


def audit_log(
    *,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    tenant_id: int | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Persist an audit row using the current request's authenticated actor."""
    row = AuditLog(
        tenant_id=tenant_id if tenant_id is not None else _current_tenant_id(),
        actor_user_id=_current_actor_id(),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details or {},
    )
    db.session.add(row)
    db.session.commit()
    return row
