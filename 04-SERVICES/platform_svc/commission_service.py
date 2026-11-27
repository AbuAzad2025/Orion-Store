"""Commission ledger service (wave 4 #39)."""

from __future__ import annotations

from decimal import Decimal

from core.utils import utc_now
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_models.financial_event import FinancialEvent

REVERSAL_ENTRY_TYPE = "commission_reversal"


class CommissionService:
    def apply_from_event(
        self,
        event: FinancialEvent,
        *,
        payment_id: int | None = None,
        order_id: int | None = None,
        commit: bool = True,
    ) -> PlatformCommissionLedger | None:
        if not event.commission_applied or not event.commission_amount:
            return None
        existing = PlatformCommissionLedger.query.filter_by(
            financial_event_id=event.id
        ).first()
        if existing:
            return existing
        entry = PlatformCommissionLedger(
            tenant_id=event.tenant_id,
            financial_event_id=event.id,
            payment_id=payment_id,
            order_id=order_id,
            gross_amount=event.amount,
            commission_percent=event.commission_percent or Decimal("0"),
            commission_amount=event.commission_amount,
            currency=event.currency,
            status="pending",
        )
        db.session.add(entry)
        db.session.flush()
        event.commission_ledger_id = entry.id
        if commit:
            db.session.commit()
        return entry

    def reverse(self, event: FinancialEvent) -> PlatformCommissionLedger | None:
        """Reverse the commission of the financial event this event offsets.

        ``event`` is normally the outbound (refund) financial event produced by
        PaymentService.refund. It carries ``reverses_financial_event_id`` in its
        metadata; we also fall back to the refund row's payment_id.
        """
        original = self._original_ledger_for_event(event)
        if original is None:
            return None
        return self._create_reversal(original, event)

    def reverse_for_payment(
        self, tenant_id: int, payment_id: int, *, refund_id: int | None = None
    ) -> PlatformCommissionLedger | None:
        """Reverse the commission booked for ``payment_id`` (tenant-scoped).

        Intended entry point for the ``payment.refunded`` domain event handler.
        Partial refunds reverse only the proportional share of commission.
        """
        payment = Payment.query.filter_by(id=payment_id, tenant_id=tenant_id).first()
        if not payment:
            return None
        if refund_id is not None:
            refund = Refund.query.filter_by(
                id=refund_id, tenant_id=tenant_id, payment_id=payment_id
            ).first()
        else:
            refund = Refund.query.filter_by(
                tenant_id=tenant_id, payment_id=payment_id
            ).first()
        if not refund or not refund.financial_event_id:
            return None
        event = FinancialEvent.query.filter_by(
            id=refund.financial_event_id, tenant_id=tenant_id
        ).first()
        if not event:
            return None
        original = self._find_original(tenant_id, payment_id)
        total = Decimal(str(payment.amount))
        ratio = (Decimal(str(refund.amount)) / total) if total else Decimal("1")
        if ratio > 1:
            ratio = Decimal("1")
        return self._create_reversal(original=original, event=event, ratio=ratio)

    def _original_ledger_for_event(
        self, event: FinancialEvent
    ) -> PlatformCommissionLedger | None:
        # Passing the original commission event directly is supported too.
        own = PlatformCommissionLedger.query.filter_by(
            tenant_id=event.tenant_id, financial_event_id=event.id
        ).first()
        if own and own.entry_type == "commission":
            return own
        metadata = event.metadata_json or {}
        original_event_id = metadata.get("reverses_financial_event_id")
        if original_event_id:
            original = PlatformCommissionLedger.query.filter_by(
                tenant_id=event.tenant_id, financial_event_id=original_event_id
            ).first()
            if original:
                return original
        if event.source_entity == "refund":
            refund = Refund.query.filter_by(
                id=event.source_id, tenant_id=event.tenant_id
            ).first()
            if refund:
                return self._find_original(event.tenant_id, refund.payment_id)
        return None

    @staticmethod
    def _find_original(
        tenant_id: int, payment_id: int
    ) -> PlatformCommissionLedger | None:
        return PlatformCommissionLedger.query.filter_by(
            tenant_id=tenant_id,
            payment_id=payment_id,
            entry_type="commission",
        ).first()

    def _create_reversal(
        self,
        original: PlatformCommissionLedger,
        event: FinancialEvent,
        ratio: Decimal = Decimal("1"),
    ) -> PlatformCommissionLedger | None:
        if original is None:
            return None
        # A full refund reverses the original entry once. Partial refunds are
        # keyed by their own (unique) financial event, so several partial
        # reversals can coexist without duplicating any single refund.
        if ratio >= Decimal("1"):
            existing = PlatformCommissionLedger.query.filter_by(
                tenant_id=original.tenant_id,
                reverses_ledger_id=original.id,
                entry_type=REVERSAL_ENTRY_TYPE,
            ).first()
        else:
            existing = PlatformCommissionLedger.query.filter_by(
                tenant_id=original.tenant_id,
                financial_event_id=event.id,
                entry_type=REVERSAL_ENTRY_TYPE,
            ).first()
        if existing:
            return existing

        # financial_event_id is UNIQUE on the ledger. When the caller passed the
        # original event itself, host the reversal in its own confirmed event.
        if event.id == original.financial_event_id:
            event = FinancialEvent(
                tenant_id=original.tenant_id,
                direction="outbound",
                event_type="commission.reversal",
                amount=-(abs(original.gross_amount) * ratio).quantize(Decimal("0.01")),
                currency=original.currency,
                source_entity="commission_ledger",
                source_id=original.id,
                commission_applied=False,
                status="completed",
                completed_at=utc_now(),
                metadata_json={"reverses_ledger_id": original.id},
            )
            db.session.add(event)
            db.session.flush()

        reversal = PlatformCommissionLedger(
            tenant_id=original.tenant_id,
            financial_event_id=event.id,
            reverses_ledger_id=original.id,
            direction="debit",
            entry_type=REVERSAL_ENTRY_TYPE,
            payment_id=original.payment_id,
            order_id=original.order_id,
            gross_amount=-(abs(original.gross_amount) * ratio).quantize(
                Decimal("0.01")
            ),
            commission_percent=original.commission_percent,
            commission_amount=-(abs(original.commission_amount) * ratio).quantize(
                Decimal("0.01")
            ),
            currency=original.currency,
            status="settled",
            notes=(
                f"reversal of commission ledger #{original.id} "
                f"via financial event #{event.id}"
            ),
        )
        db.session.add(reversal)
        db.session.flush()
        event.commission_ledger_id = reversal.id
        db.session.commit()
        return reversal
