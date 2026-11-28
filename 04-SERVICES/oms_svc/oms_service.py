"""OMS warehouse inventory and fulfillment (wave 9 #63)."""

from __future__ import annotations

import uuid

from sqlalchemy import func

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
        normalized_code = code.strip().lower()
        existing = Warehouse.query.filter_by(
            tenant_id=tenant_id, code=normalized_code
        ).first()
        if existing:
            return existing
        row = Warehouse(
            tenant_id=tenant_id,
            name=name,
            code=normalized_code,
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

    def ensure_default_warehouse(self, tenant_id: int) -> Warehouse:
        """Idempotent main warehouse — every tenant gets exactly one."""
        return self.create_warehouse(
            tenant_id=tenant_id,
            name="المستودع الرئيسي",
            code="main",
            is_default=True,
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
        if wh_id:
            wh = Warehouse.query.filter_by(id=wh_id, tenant_id=tenant_id).first()
            if not wh:
                raise NotFoundError("Warehouse not found.")
        else:
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
        product_ids = list(
            {oi.product_id for oi in order_items if oi.product_id is not None}
        )
        levels = {}
        if product_ids:
            for level in InventoryLevel.query.filter(
                InventoryLevel.warehouse_id == wh_id,
                InventoryLevel.product_id.in_(product_ids),
            ).all():
                levels[level.product_id] = level
        for oi in order_items:
            level = levels.get(oi.product_id)
            if level:
                available = level.quantity - level.reserved_quantity
                if available < oi.quantity:
                    db.session.rollback()
                    raise ValidationError("Insufficient warehouse inventory.")
                level.reserved_quantity += oi.quantity
            db.session.add(
                FulfillmentItem(
                    tenant_id=tenant_id,
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
        order_item_ids = list({fi.order_item_id for fi in items})
        order_items = {}
        product_ids = set()
        if order_item_ids:
            for oi in OrderItem.query.filter(OrderItem.id.in_(order_item_ids)).all():
                order_items[oi.id] = oi
                if oi.product_id is not None:
                    product_ids.add(oi.product_id)
        levels = {}
        if product_ids:
            for level in InventoryLevel.query.filter(
                InventoryLevel.warehouse_id == row.warehouse_id,
                InventoryLevel.product_id.in_(list(product_ids)),
            ).all():
                levels[level.product_id] = level
        for fi in items:
            oi = order_items.get(fi.order_item_id)
            if not oi:  # pragma: no cover - FK RESTRICT makes this unreachable
                continue
            level = levels.get(oi.product_id)
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
        if warehouse_id is None:
            holding = (
                InventoryLevel.query.filter_by(
                    tenant_id=tenant_id, product_id=product_id
                )
                .order_by(InventoryLevel.quantity.desc())
                .first()
            )
            warehouse_id = (
                holding.warehouse_id
                if holding
                else self.ensure_default_warehouse(tenant_id).id
            )
        wh_id = warehouse_id
        # products.quantity is the tenant-wide sellable total. Only write the
        # remainder to this warehouse so per-warehouse levels never double count.
        elsewhere = (
            db.session.query(func.coalesce(func.sum(InventoryLevel.quantity), 0))
            .filter(
                InventoryLevel.tenant_id == tenant_id,
                InventoryLevel.product_id == product_id,
                InventoryLevel.warehouse_id != wh_id,
            )
            .scalar()
            or 0
        )
        target = max(0, int(product.quantity) - int(elsewhere))
        return self.upsert_inventory(
            tenant_id=tenant_id,
            warehouse_id=wh_id,
            product_id=product_id,
            quantity=target,
        )
