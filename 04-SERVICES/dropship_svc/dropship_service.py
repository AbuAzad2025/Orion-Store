from __future__ import annotations

from decimal import Decimal

from dropship.dropship import DropshipOrder, DropshipSupplier, PodConnection

from core.exceptions import NotFoundError
from orion.extensions import db


class DropshipService:
    def create_pod_connection(
        self, *, tenant_id: int, provider: str, api_key: str, api_url: str | None = None
    ) -> PodConnection:
        import uuid

        c = PodConnection(
            tenant_id=tenant_id,
            provider=provider,
            api_key_hash=uuid.uuid4().hex,
            api_url=api_url,
        )
        db.session.add(c)
        db.session.commit()
        return c

    def create_supplier(
        self,
        *,
        tenant_id: int,
        name: str,
        contact_email: str,
        fulfillment_time_days: int = 0,
    ) -> DropshipSupplier:
        s = DropshipSupplier(
            tenant_id=tenant_id,
            name=name,
            contact_email=contact_email,
            fulfillment_time_days=fulfillment_time_days,
        )
        db.session.add(s)
        db.session.commit()
        return s

    def create_order(
        self, *, tenant_id: int, supplier_id: int, order_id: int, cost: str | Decimal
    ) -> DropshipOrder:
        d = DropshipOrder(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            order_id=order_id,
            cost=Decimal(str(cost)),
        )
        db.session.add(d)
        db.session.commit()
        return d
