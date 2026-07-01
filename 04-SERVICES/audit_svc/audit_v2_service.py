from __future__ import annotations

import uuid

from audit.audit_v2 import PlatformAdminAuditLog, PlatformAuditReport
from orion.extensions import db


class AuditV2Service:
    def create_report(self, *, report_type: str, generated_by: int, summary: dict, details: list | None = None) -> PlatformAuditReport:
        report = PlatformAuditReport(report_number=f"RPT-{uuid.uuid4().hex[:8].upper()}", report_type=report_type, generated_by=generated_by, summary=summary, details=details or [])
        db.session.add(report)
        db.session.commit()
        return report

    def log_action(self, *, user_id: int, action: str, target_type: str | None = None, target_id: int | None = None, details: dict | None = None) -> PlatformAdminAuditLog:
        log = PlatformAdminAuditLog(user_id=user_id, action=action, target_type=target_type, target_id=target_id, details=details)
        db.session.add(log)
        db.session.commit()
        return log

    def list_reports(self) -> list[PlatformAuditReport]:
        return PlatformAuditReport.query.order_by(PlatformAuditReport.created_at.desc()).all()

    def list_logs(self, limit: int = 50) -> list[PlatformAdminAuditLog]:
        return PlatformAdminAuditLog.query.order_by(PlatformAdminAuditLog.created_at.desc()).limit(limit).all()
