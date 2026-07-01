from __future__ import annotations

from accessibility.accessibility import AccessibilityAudit
from orion.extensions import db


class AccessibilityService:
    def record_audit(self, *, tenant_id: int, page_url: str, score: int, issues: list | None = None) -> AccessibilityAudit:
        audit = AccessibilityAudit(tenant_id=tenant_id, page_url=page_url, score=score, issues=issues or [])
        db.session.add(audit)
        db.session.commit()
        return audit

    def list_audits(self, tenant_id: int) -> list[AccessibilityAudit]:
        return AccessibilityAudit.query.filter_by(tenant_id=tenant_id).order_by(AccessibilityAudit.created_at.desc()).all()
