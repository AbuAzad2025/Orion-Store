"""OMS warehouse inventory and fulfillment (wave 9 #63)."""

from __future__ import annotations

import uuid

from catalog.product import Product
from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from oms.fulfillment import Fulfillment, FulfillmentItem
from oms.warehouse import InventoryLevel, Warehouse
from order.order import Order, OrderItem
from orion.extensions import db


class OmsService:
    def create_warehouse(
        self,
        *,
        tenant_id: int,
        name: str,
        code: str,
        is_default: bool = False,
        address: dict | None = None,
    ) -> Warehouse:
        row = Warehouse(
            tenant_id=tenant_id,
            name=name,
            code=code.strip().lower(),
            address=address,
            is_active=True,
            priority=0 if not is_default else 10,
        )
        db.session.add(row)
        db.session.commit()
        return row

    def list_warehouses(self, tenant_id: int) -> list[Warehouse]:
        return (
            Warehouse.query.filter_by(tenant_id=tenant_id, is_active=True)
            .order_by(Warehouse.priority.desc(), Warehouse.name)
            .all()
        )

    def get_default_warehouse(self, tenant_id: int) -> Warehouse:
        wh = (
            Warehouse.query.filter_by(tenant_id=tenant_id, is_active=True)
            .order_by(Warehouse.priority.desc())
            .first()
        )
        if not wh:
            raise NotFoundError("No warehouse configured.")
        return wh

    def upsert_inventory(
        self,
        *,
        tenant_id: int,
        warehouse_id: int,
        product_id: int,
        quantity: int,
    ) -> InventoryLevel:
        wh = Warehouse.query.filter_by(id=warehouse_id, tenant_id=tenant_id).first()
        if not wh:
            raise NotFoundError("Warehouse not found.")
        row = InventoryLevel.query.filter_by(
            warehouse_id=warehouse_id, product_id=product_id
        ).first()
        if not row:
            row = InventoryLevel(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=quantity,
            )
            db.session.add(row)
        else:
            row.quantity = quantity
        db.session.commit()
        return row

    def create_fulfillment(
        self,
        *,
        tenant_id: int,
        order_id: int,
        warehouse_id: int | None = None,
    ) -> Fulfillment:
        order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
        if not order:
            raise NotFoundError("Order not found.")
        if order.payment_status != "paid":
            raise ValidationError("Order must be paid before fulfillment.")
        wh_id = warehouse_id
        if not wh_id:
            wh_id = self.get_default_warehouse(tenant_id).id

        fulfillment = Fulfillment(
            tenant_id=tenant_id,
            order_id=order.id,
            warehouse_id=wh_id,
            fulfillment_number=f"FUL-{uuid.uuid4().hex[:8].upper()}",
            status="pending",
        )
        db.session.add(fulfillment)
        db.session.flush()

        order_items = OrderItem.query.filter_by(order_id=order.id).all()
        for oi in order_items:
            level = InventoryLevel.query.filter_by(
                warehouse_id=wh_id, product_id=oi.product_id
            ).first()
            if level:
                available = level.quantity - level.reserved_quantity
                if available < oi.quantity:
                    db.session.rollback()
                    raise ValidationError("Insufficient warehouse inventory.")
                level.reserved_quantity += oi.quantity
            db.session.add(
                FulfillmentItem(
                    fulfillment_id=fulfillment.id,
                    order_item_id=oi.id,
                    quantity=oi.quantity,
                )
            )

        order.fulfillment_status = "processing"
        db.session.commit()
        return fulfillment

    def ship_fulfillment(
        self,
        *,
        tenant_id: int,
        fulfillment_id: int,
        tracking_number: str | None = None,
    ) -> Fulfillment:
        row = Fulfillment.query.filter_by(
            id=fulfillment_id, tenant_id=tenant_id
        ).first()
        if not row:
            raise NotFoundError("Fulfillment not found.")
        if row.status not in ("pending", "picked", "packed"):
            raise ValidationError("Fulfillment cannot be shipped.")

        items = FulfillmentItem.query.filter_by(fulfillment_id=row.id).all()
        for fi in items:
            oi = OrderItem.query.get(fi.order_item_id)
            if not oi:
                continue
            level = InventoryLevel.query.filter_by(
                warehouse_id=row.warehouse_id, product_id=oi.product_id
            ).first()
            if level:
                level.quantity = max(0, level.quantity - fi.quantity)
                level.reserved_quantity = max(0, level.reserved_quantity - fi.quantity)

        row.status = "shipped"
        row.tracking_number = tracking_number
        row.shipped_at = utc_now()
        order = Order.query.get(row.order_id)
        if order:
            order.fulfillment_status = "shipped"
        db.session.commit()
        return row

    def sync_product_to_warehouse(
        self, *, tenant_id: int, product_id: int, warehouse_id: int | None = None
    ) -> InventoryLevel:
        product = Product.query.filter_by(id=product_id, tenant_id=tenant_id).first()
        if not product:
            raise NotFoundError("Product not found.")
        wh_id = warehouse_id or self.get_default_warehouse(tenant_id).id
        return self.upsert_inventory(
            tenant_id=tenant_id,
            warehouse_id=wh_id,
            product_id=product_id,
            quantity=product.quantity,
        )
