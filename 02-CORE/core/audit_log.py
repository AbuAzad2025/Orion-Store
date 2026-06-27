"""Sensitive action audit trail (§0.13.4)."""

from __future__ import annotations

from flask import g

from orion.extensions import db
from platform_models.audit_log import AuditLog


def audit_log(
    *,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    tenant_id: int | None = None,
    details: dict | None = None,
) -> AuditLog:
    row = AuditLog(
        tenant_id=tenant_id if tenant_id is not None else getattr(g, "tenant_id", None),
        actor_user_id=getattr(g, "user", None) and g.user.id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details or {},
    )
    db.session.add(row)
    db.session.commit()
    return row
