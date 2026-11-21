"""Record refunds that a payment provider already executed (webhook path).

Kept separate from ``payment_service`` so the webhook flow never shares the
outbound provider-call path — calling the provider here would create a second,
real refund at the gateway.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from core.events import publish
from core.exceptions import ConflictError, NotFoundError, ValidationError
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from platform_svc.financial_events_service import FinancialEventsService


def record_external_refund(
    *,
    tenant_id: int,
    payment_public_id: str,
    amount=None,
    provider_refund_id: str | None = None,
    reason: str | None = None,
) -> dict:
    """Record a provider-executed refund: ledger + negative event + reversal."""
    try:
        pid = uuid.UUID(str(payment_public_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise NotFoundError("Payment not found.") from exc
    payment = Payment.query.filter_by(tenant_id=tenant_id, public_id=pid).first()
    if not payment:
        raise NotFoundError("Payment not found.")
    if payment.status not in ("completed", "refunded"):
        raise ValidationError("Only completed payments can be refunded.")

    try:
        refund_amount = (
            Decimal(str(payment.amount)) if amount is None else Decimal(str(amount))
        )
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError("Invalid refund amount.") from exc
    if refund_amount <= 0:
        raise ValidationError("Refund amount must be positive.")
    if refund_amount > Decimal(str(payment.amount)):
        raise ValidationError("Refund amount exceeds payment amount.")

    # One row per provider refund id: duplicate webhooks cannot double-post.
    if (
        provider_refund_id
        and Refund.query.filter_by(
            tenant_id=tenant_id, provider_refund_id=provider_refund_id
        ).first()
    ):
        raise ConflictError("Refund already recorded.")

    refund_row = Refund(
        tenant_id=tenant_id,
        payment_id=payment.id,
        amount=refund_amount,
        currency=payment.currency,
        status="completed",
        reason=reason,
        provider_refund_id=provider_refund_id,
    )
    db.session.add(refund_row)
    db.session.flush()
    outbound = FinancialEventsService().record_outbound(
        tenant_id=tenant_id,
        amount=-refund_amount,
        event_type="payment.refund",
        source_entity="refund",
        source_id=refund_row.id,
        currency=payment.currency,
        apply_commission=False,
        allow_negative=True,
        metadata={"reverses_financial_event_id": payment.financial_event_id},
    )
    refund_row.financial_event_id = outbound.id
    if refund_amount >= Decimal(str(payment.amount)):
        payment.status = "refunded"
    db.session.commit()
    publish(
        "payment.refunded",
        order_id=payment.order_id,
        tenant_id=tenant_id,
        refund_id=refund_row.id,
        provider_refund_id=provider_refund_id,
    )
    return {
        "refund": {
            "id": refund_row.id,
            "amount": str(refund_row.amount),
            "status": refund_row.status,
            "provider_refund_id": provider_refund_id,
        },
        "financial_event": outbound.to_dict(),
        "provider_refund_id": provider_refund_id,
        "uncertain": False,
    }
