"""Voucher validation and admin CRUD (wave 6 #59)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from discount.voucher import Voucher

from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from orion.extensions import db


@dataclass(frozen=True)
class VoucherPreview:
    voucher: Voucher
    discount_amount: Decimal
    is_free_shipping: bool

    def to_dict(self) -> dict:
        return {
            "code": self.voucher.code,
            "name": self.voucher.name,
            "discount_amount": str(self.discount_amount),
            "is_free_shipping": self.is_free_shipping,
            "type": self.voucher.type,
        }


class VoucherService:
    def query_for_tenant(self, tenant_id: int):
        return Voucher.query.filter_by(tenant_id=tenant_id).order_by(Voucher.id.desc())

    def get_by_code(self, tenant_id: int, code: str) -> Voucher:
        voucher = Voucher.query.filter_by(
            tenant_id=tenant_id, code=code.strip().upper(), is_active=True
        ).first()
        if not voucher:
            raise NotFoundError(f"Voucher '{code}' not found.")
        return voucher

    def create(
        self,
        *,
        tenant_id: int,
        code: str,
        name: str,
        type: str = "percentage",
        value: str | Decimal,
        min_order_value: str | Decimal | None = None,
        max_discount_amount: str | Decimal | None = None,
        usage_limit: int | None = None,
        is_free_shipping: bool = False,
    ) -> Voucher:
        voucher = Voucher(
            tenant_id=tenant_id,
            code=code.strip().upper(),
            name=name.strip(),
            type=type,
            value=Decimal(str(value)),
            min_order_value=(
                Decimal(str(min_order_value)) if min_order_value is not None else None
            ),
            max_discount_amount=(
                Decimal(str(max_discount_amount))
                if max_discount_amount is not None
                else None
            ),
            usage_limit=usage_limit,
            is_free_shipping=is_free_shipping,
        )
        db.session.add(voucher)
        db.session.commit()
        return voucher

    def validate(self, tenant_id: int, code: str, subtotal: Decimal) -> VoucherPreview:
        voucher = self.get_by_code(tenant_id, code)
        now = utc_now()
        if voucher.start_date and now < voucher.start_date:
            raise ValidationError("Voucher is not active yet.")
        if voucher.end_date and now > voucher.end_date:
            raise ValidationError("Voucher has expired.")
        if (
            voucher.usage_limit is not None
            and voucher.usage_count >= voucher.usage_limit
        ):
            raise ValidationError("Voucher usage limit reached.")
        if voucher.min_order_value and subtotal < voucher.min_order_value:
            raise ValidationError("Order subtotal below voucher minimum.")

        discount = self._compute_discount(voucher, subtotal)
        return VoucherPreview(
            voucher=voucher,
            discount_amount=discount,
            is_free_shipping=voucher.is_free_shipping,
        )

    def _compute_discount(self, voucher: Voucher, subtotal: Decimal) -> Decimal:
        if voucher.type == "fixed_amount":
            amount = min(voucher.value, subtotal)
        else:
            amount = (subtotal * voucher.value / Decimal("100")).quantize(
                Decimal("0.01")
            )
            if voucher.max_discount_amount is not None:
                amount = min(amount, voucher.max_discount_amount)
        return max(amount, Decimal("0"))

    def record_usage(self, voucher: Voucher) -> None:
        voucher.usage_count += 1
        db.session.add(voucher)
