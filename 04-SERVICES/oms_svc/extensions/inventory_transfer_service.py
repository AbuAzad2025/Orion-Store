from __future__ import annotations

import uuid

from core.exceptions import NotFoundError, ValidationError
from oms.inventory_transfer import InventoryTransfer, InventoryTransferItem
from oms.warehouse import InventoryLevel, Warehouse
from orion.extensions import db


class InventoryTransferService:
    def create_transfer(
        self,
        *,
        tenant_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        notes: str | None = None,
    ) -> InventoryTransfer:
        from_wh = Warehouse.query.filter_by(
            id=from_warehouse_id, tenant_id=tenant_id
        ).first()
        to_wh = Warehouse.query.filter_by(
            id=to_warehouse_id, tenant_id=tenant_id
        ).first()
        if not from_wh or not to_wh:
            raise NotFoundError("Warehouse not found.")
        if from_warehouse_id == to_warehouse_id:
            raise ValidationError("Source and destination must differ.")
        transfer = InventoryTransfer(
            tenant_id=tenant_id,
            transfer_number=f"TRF-{tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            notes=notes,
        )
        db.session.add(transfer)
        db.session.commit()
        return transfer

    def add_item(
        self, *, tenant_id: int, transfer_id: int, product_id: int, quantity: int
    ) -> InventoryTransferItem:
        transfer = InventoryTransfer.query.filter_by(
            id=transfer_id, tenant_id=tenant_id
        ).first()
        if not transfer:
            raise NotFoundError("Transfer not found.")
        if transfer.status != "draft":
            raise ValidationError("Transfer is not in draft status.")
        item = InventoryTransferItem(
            transfer_id=transfer_id, product_id=product_id, quantity=quantity
        )
        db.session.add(item)
        db.session.commit()
        return item

    def complete_transfer(
        self, *, tenant_id: int, transfer_id: int
    ) -> InventoryTransfer:
        transfer = InventoryTransfer.query.filter_by(
            id=transfer_id, tenant_id=tenant_id
        ).first()
        if not transfer:
            raise NotFoundError("Transfer not found.")
        if transfer.status != "draft":
            raise ValidationError("Transfer is not in draft status.")
        items = InventoryTransferItem.query.filter_by(transfer_id=transfer.id).all()
        if not items:
            raise ValidationError("Transfer has no items.")
        for item in items:
            from_level = InventoryLevel.query.filter_by(
                warehouse_id=transfer.from_warehouse_id,
                product_id=item.product_id,
                tenant_id=tenant_id,
            ).first()
            if not from_level or from_level.quantity < item.quantity:
                raise ValidationError(
                    f"Insufficient stock for product {item.product_id}."
                )
            from_level.quantity -= item.quantity
            to_level = InventoryLevel.query.filter_by(
                warehouse_id=transfer.to_warehouse_id,
                product_id=item.product_id,
                tenant_id=tenant_id,
            ).first()
            if to_level:
                to_level.quantity += item.quantity
            else:
                db.session.add(
                    InventoryLevel(
                        warehouse_id=transfer.to_warehouse_id,
                        tenant_id=tenant_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                    )
                )
        from datetime import datetime, timezone

        transfer.status = "completed"
        transfer.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return transfer
