from __future__ import annotations

from core.exceptions import NotFoundError
from orion.extensions import db
from stock_notification.stock_notification import StockNotification


class StockNotificationService:
    def subscribe(self, *, tenant_id: int, product_id: int, customer_email: str) -> StockNotification:
        existing = StockNotification.query.filter_by(tenant_id=tenant_id, product_id=product_id, customer_email=customer_email.strip().lower(), is_notified=False).first()
        if existing:
            return existing
        n = StockNotification(tenant_id=tenant_id, product_id=product_id, customer_email=customer_email.strip().lower())
        db.session.add(n)
        db.session.commit()
        return n

    def notify_for_product(self, *, tenant_id: int, product_id: int) -> int:
        subscribers = StockNotification.query.filter_by(tenant_id=tenant_id, product_id=product_id, is_notified=False).all()
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        for s in subscribers:
            s.is_notified = True
            s.notified_at = now
        db.session.commit()
        return len(subscribers)
