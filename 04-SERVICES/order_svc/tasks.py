"""Background jobs for manual (WhatsApp) orders."""

from __future__ import annotations

from sqlalchemy import text

from core.middleware import bind_task_rls_context
from orion.celery_app import celery_app
from orion.extensions import db
from order_svc.whatsapp_order_service import WhatsAppOrderService


@celery_app.task(name="orion.expire_whatsapp_orders")
def expire_whatsapp_orders() -> int:
    """Auto-cancel undecided WhatsApp orders older than two weeks."""
    bind_task_rls_context(is_platform_admin=True)
    db.session.execute(text("SELECT set_config('app.is_platform_admin','true',true)"))
    return WhatsAppOrderService().expire_stale()
