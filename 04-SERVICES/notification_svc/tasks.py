"""Celery tasks for notifications and housekeeping."""

from __future__ import annotations

from orion.celery_app import celery_app


@celery_app.task(name="orion.send_email")
def send_email_task(payload: dict) -> dict:
    from core.i18n_messages import localize
    from notification_svc.email_sender import render_order_confirmation, send_smtp_email

    template = payload.get("template")
    context = payload.get("context") or {}
    locale = payload.get("locale")
    if template == "order_confirmation":
        subject, body = render_order_confirmation(context, locale=locale)
    else:
        subject = f"Azadexa — {template}"
        body = f"{localize('تفاصيل', 'Details', locale)}\n" + "\n".join(
            f"{k}: {v}" for k, v in context.items()
        )
    send_smtp_email(recipient=payload["recipient"], subject=subject, body=body)
    return {"status": "sent", "recipient": payload["recipient"]}


@celery_app.task(name="orion.check_trial_expiry")
def check_trial_expiry_task() -> int:
    from base.types import TenantStatus
    from core.middleware import bind_task_rls_context
    from core.utils import utc_now
    from orion.extensions import db
    from tenant.tenant import Tenant

    # Tenant rows span all tenants → run with platform-admin context.
    bind_task_rls_context(is_platform_admin=True)
    expired = (
        Tenant.query.filter(
            Tenant.status == TenantStatus.TRIAL.value,
            Tenant.deleted_at.is_(None),
            Tenant.trial_ends_at.isnot(None),
            Tenant.trial_ends_at < utc_now(),
        )
        .limit(200)
        .all()
    )
    for tenant in expired:
        tenant.status = TenantStatus.SUSPENDED.value
    if expired:
        db.session.commit()
    return len(expired)


@celery_app.task(name="orion.reconciliation.run_nightly")
def run_nightly_reconciliation_task() -> dict:
    """Settle confirmed commissions, one tenant at a time (§0.15 gap closure)."""
    from core.middleware import bind_task_rls_context
    from platform_svc.reconciliation_service import ReconciliationService

    # Tenant enumeration spans all tenants → platform-admin context. Settlement
    # itself is tenant-scoped inside ReconciliationService.
    bind_task_rls_context(is_platform_admin=True)
    return ReconciliationService().run()
