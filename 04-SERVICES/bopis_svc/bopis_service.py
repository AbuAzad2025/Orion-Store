from __future__ import annotations

from bopis.bopis import PickupLocation, PickupSlot

from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class BopisService:
    def create_location(
        self,
        *,
        tenant_id: int,
        code: str,
        name: str,
        address: dict,
        warehouse_id: int | None = None,
        phone: str | None = None,
    ) -> PickupLocation:
        loc = PickupLocation(
            tenant_id=tenant_id,
            code=code,
            name=name,
            address=address,
            warehouse_id=warehouse_id,
            phone=phone,
        )
        db.session.add(loc)
        db.session.commit()
        return loc

    def list_locations(self, tenant_id: int) -> list[PickupLocation]:
        return PickupLocation.query.filter_by(tenant_id=tenant_id, is_active=True).all()

    def create_slot(
        self,
        *,
        location_id: int,
        tenant_id: int,
        day_of_week: int,
        start_time: str,
        end_time: str,
        max_orders: int = 10,
    ) -> PickupSlot:
        slot = PickupSlot(
            location_id=location_id,
            tenant_id=tenant_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            max_orders=max_orders,
        )
        db.session.add(slot)
        db.session.commit()
        return slot

    def book_checkout(self, *, location_id: int, tenant_id: int, order_id: int) -> dict:
        from datetime import datetime

        now = datetime.utcnow()
        day = now.weekday()
        slot = PickupSlot.query.filter_by(
            location_id=location_id,
            tenant_id=tenant_id,
            day_of_week=day,
            is_active=True,
        ).first()
        if not slot:
            raise ValidationError("No pickup slot available today.")
        if slot.current_orders >= slot.max_orders:
            raise ValidationError("Pickup slot is full.")
        slot.current_orders += 1
        db.session.commit()
        return {
            "location_id": location_id,
            "slot_id": slot.id,
            "day_of_week": day,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
        }
