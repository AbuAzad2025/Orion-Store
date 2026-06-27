"""Transactional notification queue (MVP stub — §18)."""

from __future__ import annotations

from order.order import Order


class NotificationService:
    """Enqueue order/lifecycle messages — email provider wired in v1.1."""

    def enqueue(
        self,
        *,
        tenant_id: int,
        channel: str,
        template: str,
        recipient: str,
        context: dict | None = None,
    ) -> dict:
        return {
            "tenant_id": tenant_id,
            "channel": channel,
            "template": template,
            "recipient": recipient,
            "context": context or {},
            "status": "queued",
        }

    def send_order_confirmation(self, order: Order) -> dict:
        return self.enqueue(
            tenant_id=order.tenant_id,
            channel="email",
            template="order_confirmation",
            recipient=order.customer_email,
            context={
                "order_number": order.order_number,
                "total": str(order.total),
            },
        )
