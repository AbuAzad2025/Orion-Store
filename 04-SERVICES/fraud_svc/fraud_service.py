from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import g, has_request_context
from fraud.fraud import Chargeback, FraudReview, FraudRule

from core.exceptions import NotFoundError
from orion.extensions import db

# Points contributed to the risk score when a rule matches. The final score is
# always clamped to the 0-100 range before a review is persisted.
_RULE_WEIGHTS: dict[str, int] = {
    "amount": 40,
    "order_amount": 40,
    "total": 40,
    "order_total": 40,
    "first_order": 30,
    "email_first_time": 30,
    "new_customer": 30,
    "first_time_email": 30,
    "velocity": 35,
    "guest": 15,
    "guest_order": 15,
}
_DEFAULT_RULE_WEIGHT = 20


def _compare(left: Decimal, operator: str, right: Decimal) -> bool:
    """Evaluate a simple numeric comparison used by fraud rules."""
    op = (operator or "").strip().lower()
    if op in (">", "gt"):
        return left > right
    if op in (">=", "gte"):
        return left >= right
    if op in ("<", "lt"):
        return left < right
    if op in ("<=", "lte"):
        return left <= right
    if op in ("==", "=", "eq"):
        return left == right
    if op in ("!=", "neq"):
        return left != right
    return False


class FraudService:
    def create_rule(
        self,
        *,
        tenant_id: int,
        name: str,
        rule_type: str,
        operator: str,
        threshold_value: str | Decimal,
        action: str = "review",
    ) -> FraudRule:
        r = FraudRule(
            tenant_id=tenant_id,
            name=name,
            rule_type=rule_type,
            operator=operator,
            threshold_value=Decimal(str(threshold_value)),
            action=action,
        )
        db.session.add(r)
        db.session.commit()
        return r

    def list_rules(self, tenant_id: int) -> list[FraudRule]:
        return FraudRule.query.filter_by(tenant_id=tenant_id).all()

    @staticmethod
    def _rule_metric(rule_type: str | None, order, context: dict) -> Decimal:
        """Resolve the numeric value a rule is evaluated against."""
        rt = (rule_type or "").strip().lower()
        if rt in ("amount", "order_amount", "total", "order_total"):
            return Decimal(str(order.total or 0))
        if rt in (
            "first_order",
            "email_first_time",
            "new_customer",
            "first_time_email",
        ):
            is_first = context.get("is_first_order")
            if is_first is None:
                is_first = (
                    type(order)
                    .query.filter_by(
                        tenant_id=order.tenant_id, customer_email=order.customer_email
                    )
                    .count()
                    <= 1
                )
            return Decimal(1 if is_first else 0)
        if rt in ("guest", "guest_order"):
            return Decimal(1 if order.is_guest else 0)
        # Allow callers to feed custom rule types directly through context.
        if rt in context:
            try:
                return Decimal(str(context[rt]))
            except (TypeError, ValueError, InvalidOperation):
                return Decimal(0)
        return Decimal(0)

    def evaluate_order(
        self,
        tenant_id: int,
        order_id: int,
        context: dict | None = None,
    ) -> dict:
        """Evaluate all active tenant rules for an order.

        Returns a decision dict. Creating a :class:`FraudReview` is idempotent
        per (tenant, order): repeated calls never duplicate a review.
        """
        from order.order import Order

        context = dict(context or {})
        order = Order.query.filter_by(id=order_id, tenant_id=tenant_id).first()
        if not order:
            raise NotFoundError("Order not found.")

        existing = FraudReview.query.filter_by(
            tenant_id=tenant_id, order_id=order_id
        ).first()
        if existing:
            return {
                "tenant_id": tenant_id,
                "order_id": order_id,
                "risk_score": existing.risk_score,
                "decision": "review",
                "review": existing.to_dict(),
                "matched_rules": [],
                "created": False,
            }

        rules = FraudRule.query.filter_by(tenant_id=tenant_id, is_active=True).all()
        score = 0
        matched: list[str] = []
        for rule in rules:
            value = self._rule_metric(rule.rule_type, order, context)
            if _compare(value, rule.operator, Decimal(str(rule.threshold_value))):
                matched.append(rule.name)
                score += _RULE_WEIGHTS.get(
                    (rule.rule_type or "").strip().lower(), _DEFAULT_RULE_WEIGHT
                )
        score = max(0, min(100, int(score)))

        result: dict = {
            "tenant_id": tenant_id,
            "order_id": order_id,
            "risk_score": score,
            "decision": "review" if matched else "approve",
            "review": None,
            "matched_rules": matched,
            "created": False,
        }
        if not matched:
            return result

        reviewer = context.get("reviewed_by")
        if reviewer is None and has_request_context():
            user = getattr(g, "user", None)
            reviewer = getattr(user, "id", None) if user else None

        fr = FraudReview(
            tenant_id=tenant_id,
            order_id=order_id,
            risk_score=score,
            reviewed_by=reviewer,
            notes="Matched rules: " + ", ".join(matched),
        )
        db.session.add(fr)
        db.session.commit()
        result["review"] = fr.to_dict()
        result["created"] = True
        return result

    def review_order(
        self, *, tenant_id: int, order_id: int, risk_score: int
    ) -> FraudReview:
        risk_score = max(0, min(100, int(risk_score)))
        fr = FraudReview(tenant_id=tenant_id, order_id=order_id, risk_score=risk_score)
        db.session.add(fr)
        db.session.commit()
        return fr

    def chargeback(
        self,
        *,
        tenant_id: int,
        payment_id: int,
        order_id: int,
        amount: str | Decimal,
        reason_code: str | None = None,
    ) -> Chargeback:
        cb = Chargeback(
            tenant_id=tenant_id,
            payment_id=payment_id,
            order_id=order_id,
            amount=Decimal(str(amount)),
            reason_code=reason_code,
        )
        db.session.add(cb)
        db.session.commit()
        return cb


def on_order_created(**payload) -> None:
    """Domain subscriber for ``order.created``.

    Evaluation only records a review; it must never fail the order that was
    just created, so every error is swallowed and the session rolled back.
    """
    tenant_id = payload.get("tenant_id")
    order_id = payload.get("order_id")
    if not tenant_id or not order_id:
        return
    try:
        FraudService().evaluate_order(
            tenant_id=int(tenant_id),
            order_id=int(order_id),
            context=payload.get("context"),
        )
    except Exception:  # pragma: no cover - defensive: never block checkout
        db.session.rollback()


def install_order_created_subscriber() -> None:
    """Register the fraud subscriber on the shared domain event bus."""
    from core.events import subscribe

    subscribe("order.created", on_order_created)
