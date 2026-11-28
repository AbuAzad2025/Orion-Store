"""Transactional notifications — SMTP + Celery (§18, wave 15)."""

from __future__ import annotations

from notification_svc.email_sender import smtp_configured
from order.order import Order


class NotificationService:
    def enqueue(
        self,
        *,
        tenant_id: int,
        channel: str,
        template: str,
        recipient: str,
        context: dict | None = None,
    ) -> dict:
        payload = {
            "tenant_id": tenant_id,
            "channel": channel,
            "template": template,
            "recipient": recipient,
            "context": context or {},
            "status": "queued",
        }
        if channel == "email":
            self._dispatch_email(payload)
        return payload

    def _dispatch_email(self, payload: dict) -> None:
        if not smtp_configured():
            return
        if not str(payload.get("recipient") or "").strip():
            return  # WhatsApp orders without a real email must not bounce SMTP
        from flask import current_app

        from notification_svc.tasks import send_email_task

        if current_app.config.get("CELERY_TASK_ALWAYS_EAGER"):
            send_email_task(payload)
            payload["status"] = "sent"
        else:
            send_email_task.delay(payload)

    def send_order_confirmation(self, order: Order) -> dict:
        return self.enqueue(
            tenant_id=order.tenant_id,
            channel="email",
            template="order_confirmation",
            recipient=(
                ""
                if (order.customer_email or "").endswith("@whatsapp.pending")
                else order.customer_email
            ),
            context={
                "order_number": order.order_number,
                "total": str(order.total),
            },
        )

    def send_action_email(
        self,
        *,
        tenant_id: int,
        recipient: str,
        template: str,
        context: dict | None = None,
    ) -> dict:
        """Dispatch an email produced by a workflow ``send_email`` action."""
        return self.enqueue(
            tenant_id=tenant_id,
            channel="email",
            template=template,
            recipient=recipient,
            context=context or {},
        )
