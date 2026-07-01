from __future__ import annotations

from decimal import Decimal

from core.exceptions import NotFoundError
from fraud.fraud import Chargeback, FraudReview, FraudRule
from orion.extensions import db


class FraudService:
    def create_rule(self, *, tenant_id: int, name: str, rule_type: str, operator: str, threshold_value: str | Decimal, action: str = "review") -> FraudRule:
        r = FraudRule(tenant_id=tenant_id, name=name, rule_type=rule_type, operator=operator, threshold_value=Decimal(str(threshold_value)), action=action)
        db.session.add(r)
        db.session.commit()
        return r

    def list_rules(self, tenant_id: int) -> list[FraudRule]:
        return FraudRule.query.filter_by(tenant_id=tenant_id).all()

    def review_order(self, *, tenant_id: int, order_id: int, risk_score: int) -> FraudReview:
        fr = FraudReview(tenant_id=tenant_id, order_id=order_id, risk_score=risk_score)
        db.session.add(fr)
        db.session.commit()
        return fr

    def chargeback(self, *, tenant_id: int, payment_id: int, order_id: int, amount: str | Decimal, reason_code: str | None = None) -> Chargeback:
        cb = Chargeback(tenant_id=tenant_id, payment_id=payment_id, order_id=order_id, amount=Decimal(str(amount)), reason_code=reason_code)
        db.session.add(cb)
        db.session.commit()
        return cb
