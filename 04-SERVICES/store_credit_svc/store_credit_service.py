from __future__ import annotations

from decimal import Decimal

from core.exceptions import NotFoundError, ValidationError
from core.utils import utc_now
from orion.extensions import db
from store_credit.store_credit import StoreCredit, StoreCreditTransaction


class StoreCreditService:
    def get_or_create(self, *, tenant_id: int, customer_email: str) -> StoreCredit:
        credit = StoreCredit.query.filter_by(tenant_id=tenant_id, customer_email=customer_email.strip().lower()).first()
        if credit:
            return credit
        credit = StoreCredit(tenant_id=tenant_id, customer_email=customer_email.strip().lower())
        db.session.add(credit)
        db.session.commit()
        return credit

    def add_funds(self, *, tenant_id: int, customer_email: str, amount: str | Decimal, reason: str | None = None) -> StoreCredit:
        credit = self.get_or_create(tenant_id=tenant_id, customer_email=customer_email)
        dec = Decimal(str(amount))
        if dec <= 0:
            raise ValidationError("Amount must be positive.")
        credit.balance += dec
        db.session.add(StoreCreditTransaction(
            credit_id=credit.id, tenant_id=tenant_id, transaction_type="credit",
            amount=dec, balance_after=credit.balance, reason=reason,
        ))
        db.session.commit()
        return credit

    def deduct(self, *, tenant_id: int, customer_email: str, amount: str | Decimal, reference_type: str | None = None, reference_id: int | None = None) -> StoreCredit:
        credit = self.get_or_create(tenant_id=tenant_id, customer_email=customer_email)
        dec = Decimal(str(amount))
        if dec <= 0:
            raise ValidationError("Amount must be positive.")
        if credit.balance < dec:
            raise ValidationError("Insufficient store credit.")
        credit.balance -= dec
        db.session.add(StoreCreditTransaction(
            credit_id=credit.id, tenant_id=tenant_id, transaction_type="debit",
            amount=dec, balance_after=credit.balance, reference_type=reference_type, reference_id=reference_id,
        ))
        db.session.commit()
        return credit

    def get_balance(self, *, tenant_id: int, customer_email: str) -> Decimal:
        credit = StoreCredit.query.filter_by(tenant_id=tenant_id, customer_email=customer_email.strip().lower()).first()
        return credit.balance if credit else Decimal("0")

    def list_transactions(self, *, tenant_id: int, credit_id: int) -> list[StoreCreditTransaction]:
        return StoreCreditTransaction.query.filter_by(credit_id=credit_id, tenant_id=tenant_id).order_by(StoreCreditTransaction.created_at.desc()).all()
