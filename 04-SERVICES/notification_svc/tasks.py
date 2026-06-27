"""Celery tasks for notifications and housekeeping."""

from __future__ import annotations

from orion.celery_app import celery_app


@celery_app.task(name="orion.send_email")
def send_email_task(payload: dict) -> dict:
    from notification_svc.email_sender import render_order_confirmation, send_smtp_email

    template = payload.get("template")
    context = payload.get("context") or {}
    if template == "order_confirmation":
        subject, body = render_order_confirmation(context)
    else:
        subject = f"Azadexa — {template}"
        body = str(context)
    send_smtp_email(recipient=payload["recipient"], subject=subject, body=body)
    return {"status": "sent", "recipient": payload["recipient"]}


@celery_app.task(name="orion.check_trial_expiry")
def check_trial_expiry_task() -> int:
    from base.types import TenantStatus
    from orion.extensions import db
    from tenant.tenant import Tenant

    expired = (
        Tenant.query.filter_by(status=TenantStatus.TRIAL.value, deleted_at=None)
        .limit(200)
        .all()
    )
    for tenant in expired:
        tenant.status = TenantStatus.SUSPENDED.value
    if expired:
        db.session.commit()
    return len(expired)
