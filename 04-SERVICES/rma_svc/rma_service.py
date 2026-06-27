"""RMA return management (wave 9 #63)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from order.order import Order, OrderItem
from orion.extensions import db
from payment.payment import Payment
from returns.merchandise_return import MerchandiseReturn, ReturnItem
from returns.return_reason import ReturnReason


class RmaService:
    DEFAULT_REASONS = (
        ("defective", "منتج معيب"),
        ("wrong_item", "منتج خاطئ"),
        ("changed_mind", "تغيير رأي"),
    )

    def ensure_reasons_seeded(self, tenant_id: int) -> None:
        for code, label in self.DEFAULT_REASONS:
            if ReturnReason.query.filter_by(tenant_id=tenant_id, code=code).first():
                continue
            db.session.add(
                ReturnReason(
                    tenant_id=tenant_id,
                    code=code,
                    label=label,
                    is_active=True,
                )
            )
        db.session.commit()

    def list_reasons(self, tenant_id: int) -> list[ReturnReason]:
        self.ensure_reasons_seeded(tenant_id)
        return (
            ReturnReason.query.filter_by(tenant_id=tenant_id, is_active=True)
            .order_by(ReturnReason.sort_order, ReturnReason.code)
            .all()
        )

    def create_return(
        self,
        *,
        tenant_id: int,
        order_id: int,
        items: list[dict],
        return_type: str = "refund",
        reason_code: str | None = None,
        reason_note: str | None = None,
        user_id: int | None = None,
    ) -> MerchandiseReturn:
        order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
        if not order:
            raise NotFoundError("Order not found.")
        if order.payment_status != "paid":
            raise ValidationError("Only paid orders can be returned.")

        reason_id = None
        if reason_code:
            self.ensure_reasons_seeded(tenant_id)
            reason = ReturnReason.query.filter_by(
                tenant_id=tenant_id, code=reason_code
            ).first()
            if reason:
                reason_id = reason.id

        refund_total = Decimal("0")
        return_row = MerchandiseReturn(
            tenant_id=tenant_id,
            return_number=f"RMA-{tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            order_id=order.id,
            user_id=user_id,
            return_type=return_type,
            reason_id=reason_id,
            reason_note=reason_note,
            status="requested",
        )
        db.session.add(return_row)
        db.session.flush()

        for raw in items:
            oi = OrderItem.query.filter_by(
                id=raw["order_item_id"], order_id=order.id, tenant_id=tenant_id
            ).first()
            if not oi:
                raise NotFoundError("Order item not found.")
            qty = int(raw.get("quantity", 1))
            if qty < 1 or qty > oi.quantity:
                raise ValidationError("Invalid return quantity.")
            line_refund = (oi.unit_price * qty).quantize(Decimal("0.01"))
            refund_total += line_refund
            db.session.add(
                ReturnItem(
                    return_id=return_row.id,
                    order_item_id=oi.id,
                    product_id=oi.product_id,
                    quantity=qty,
                    condition=raw.get("condition", "new"),
                    restock=bool(raw.get("restock", True)),
                    refund_amount=line_refund,
                )
            )

        return_row.refund_amount = refund_total
        db.session.commit()
        return return_row

    def get_return(self, tenant_id: int, return_id: int) -> MerchandiseReturn:
        row = MerchandiseReturn.query.filter_by(
            id=return_id, tenant_id=tenant_id
        ).first()
        if not row:
            raise NotFoundError("Return not found.")
        return row

    def list_returns(self, tenant_id: int) -> list[MerchandiseReturn]:
        return (
            MerchandiseReturn.query.filter_by(tenant_id=tenant_id)
            .order_by(MerchandiseReturn.created_at.desc())
            .all()
        )

    def approve_return(
        self,
        *,
        tenant_id: int,
        return_id: int,
        approved_by: int | None = None,
    ) -> MerchandiseReturn:
        row = self.get_return(tenant_id, return_id)
        if row.status != "requested":
            raise ValidationError("Return is not pending approval.")
        row.status = "approved"
        row.approved_by = approved_by
        row.received_at = utc_now()
        db.session.commit()
        return row

    def complete_return(
        self,
        *,
        tenant_id: int,
        return_id: int,
        process_refund: bool = True,
    ) -> dict:
        row = self.get_return(tenant_id, return_id)
        if row.status not in ("approved", "received"):
            raise ValidationError("Return must be approved first.")

        items = ReturnItem.query.filter_by(return_id=row.id).all()
        for item in items:
            if item.restock and item.product_id:
                from catalog.product import Product

                prod = Product.query.filter_by(
                    id=item.product_id, tenant_id=tenant_id
                ).first()
                if prod:
                    prod.quantity += item.quantity

        refund_result = None
        if process_refund and row.return_type == "refund" and row.refund_amount > 0:
            payment = Payment.query.filter_by(
                tenant_id=tenant_id, order_id=row.order_id, status="completed"
            ).first()
            if payment:
                from payment_svc.payment_service import PaymentService

                refund_result = PaymentService().refund(
                    tenant_id=tenant_id,
                    payment_public_id=str(payment.public_id),
                    reason=f"RMA {row.return_number}",
                )

        row.status = "refunded" if row.return_type == "refund" else "closed"
        row.completed_at = utc_now()
        db.session.commit()
        return {"return": row.to_dict(), "refund": refund_result}
