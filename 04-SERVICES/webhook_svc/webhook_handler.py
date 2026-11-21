"""Real financial side effects for verified payment webhooks.

The HTTP layer only invokes these handlers *after* signature verification,
webhook-event claiming (replay prevention) and tenant/RLS context bootstrap.

Design constraints
------------------
* ``payment_service`` is deliberately not modified.  Confirmations are
  composed from the public service APIs it already uses internally:
  ``OrderService.mark_paid``, ``FinancialEventsService.record_inbound`` and
  ``CommissionService.apply_from_event``.  Refunds delegate to the public
  ``PaymentService.refund`` entry point.
* Every handler is idempotent on its own: a capture only touches a payment in
  ``pending``/``processing`` state and a refund only touches a ``completed``
  one.  This is a second line of defence behind ``claim_webhook_event``.
"""

from __future__ import annotations

import uuid
from typing import Any

from core.events import publish
from core.exceptions import NotFoundError
from order.order import Order
from order_svc.order_service import OrderService
from orion.extensions import db
from payment.payment import Payment
from payment_svc.payment_service import PaymentService
from platform_svc.commission_service import CommissionService
from platform_svc.financial_events_service import FinancialEventsService

# Keys that may carry a public order / payment identifier in provider payloads.
_ORDER_KEYS = (
    "order_public_id",
    "order_public",
    "client_reference_id",
    "custom_id",
    "order_id",
    "reference",
)
_PAYMENT_KEYS = ("payment_public_id", "payment_public", "payment_id")
_PROVIDER_KEYS = (
    "provider_payment_id",
    "payment_intent",
    "transaction_id",
    "external_id",
    "capture_id",
    "id",
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _objects(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Provider payload shapes we understand (Stripe / PayPal / BNPL)."""
    result: list[dict[str, Any]] = [payload]
    data = _as_dict(payload.get("data"))
    if data:
        result.append(data)
        obj = _as_dict(data.get("object"))
        if obj:
            result.append(obj)
    resource = _as_dict(payload.get("resource"))
    if resource:
        result.append(resource)
    return result


def _blocks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Top-level and nested metadata blocks, searched for identifiers."""
    result: list[dict[str, Any]] = []
    for obj in _objects(payload):
        metadata = _as_dict(obj.get("metadata"))
        if metadata:
            result.append(metadata)
    return result


def _values(payload: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for source in _objects(payload) + _blocks(payload):
        for key in keys:
            value = source.get(key)
            if value is not None and str(value):
                found.append(str(value))
    return found


def _provider_ids(payload: dict[str, Any]) -> list[str]:
    """Provider transaction ids — never the top-level webhook event id."""
    found: list[str] = []
    for source in _objects(payload)[1:] + _blocks(payload):
        for key in _PROVIDER_KEYS:
            value = source.get(key)
            if isinstance(value, str) and value:
                found.append(value)
    return found


class WebhookEffectHandler:
    """Apply the money movement described by an already-verified webhook."""

    def __init__(self) -> None:
        # Only public service APIs — no edits to payment_service / models.
        self._orders = OrderService()
        self._financial = FinancialEventsService()
        self._commission = CommissionService()

    # -- public entry points -------------------------------------------------

    def handle_stripe_payment_succeeded(
        self, tenant_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self._capture(
            tenant_id,
            payload,
            provider="stripe",
            event_type="stripe.payment_succeeded",
        )

    def handle_paypal_capture_completed(
        self, tenant_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self._capture(
            tenant_id,
            payload,
            provider="paypal",
            event_type="paypal.capture_completed",
        )

    def handle_bnpl_captured(
        self, tenant_id: int, payload: dict[str, Any], *, provider: str = "bnpl"
    ) -> dict[str, Any]:
        return self._capture(
            tenant_id,
            payload,
            provider=provider,
            event_type=f"{provider}.captured",
        )

    def handle_refund(
        self, tenant_id: int, payload: dict[str, Any], *, provider: str = "stripe"
    ) -> dict[str, Any]:
        order = self._resolve_order(tenant_id, payload)
        payment = self._resolve_payment(
            tenant_id, payload, statuses=("completed",), order=order
        )
        if payment is None:
            return {"processed": False, "reason": "no_completed_payment"}

        # Public PaymentService API: creates the Refund row, the outbound
        # financial event and the commission reversal (via domain event).
        result = PaymentService().refund(
            tenant_id=tenant_id,
            payment_public_id=str(payment.public_id),
            reason=f"{provider} webhook refund",
        )
        return {
            "processed": True,
            "payment": payment.to_dict(),
            "refund": result["refund"],
            "financial_event": result["financial_event"],
        }

    # -- internals -----------------------------------------------------------

    def _resolve_order(self, tenant_id: int, payload: dict[str, Any]) -> Order | None:
        for candidate in _values(payload, _ORDER_KEYS):
            try:
                return self._orders.get_by_public_id(tenant_id, candidate)
            except NotFoundError:
                continue
        return None

    def _resolve_payment(
        self,
        tenant_id: int,
        payload: dict[str, Any],
        *,
        statuses: tuple[str, ...],
        order: Order | None = None,
    ) -> Payment | None:
        query = Payment.query.filter_by(tenant_id=tenant_id)

        # Explicit identifiers win; they work even without an order reference.
        for candidate in _values(payload, _PAYMENT_KEYS):
            try:
                public_id = uuid.UUID(candidate)
            except (ValueError, TypeError, AttributeError):
                continue
            payment = query.filter_by(public_id=public_id).first()
            if payment is not None and payment.status in statuses:
                return payment

        for candidate in _provider_ids(payload):
            payment = query.filter_by(provider_payment_id=candidate).first()
            if payment is not None and payment.status in statuses:
                return payment

        # Fallback: only when the order was resolved, and only if there is
        # exactly one eligible payment — never guess between several.
        if order is not None:
            candidates = (
                query.filter_by(order_id=order.id)
                .filter(Payment.status.in_(statuses))
                .order_by(Payment.id.desc())
                .all()
            )
            if len(candidates) == 1:
                return candidates[0]
        return None

    def _capture(
        self,
        tenant_id: int,
        payload: dict[str, Any],
        *,
        provider: str,
        event_type: str,
    ) -> dict[str, Any]:
        order = self._resolve_order(tenant_id, payload)
        payment = self._resolve_payment(
            tenant_id, payload, statuses=("pending", "processing"), order=order
        )
        if payment is None:
            return {"processed": False, "reason": "no_pending_payment"}

        provider_id = next(iter(_provider_ids(payload)), None)
        if provider_id:
            payment.provider_payment_id = provider_id
        payment.status = "completed"
        db.session.flush()

        event = self._financial.record_inbound(
            tenant_id=tenant_id,
            amount=payment.amount,
            event_type=event_type,
            source_entity="payment",
            source_id=payment.id,
            currency=payment.currency,
            description=f"{provider} webhook capture",
        )
        payment.financial_event_id = event.id
        ledger = self._commission.apply_from_event(
            event, payment_id=payment.id, order_id=payment.order_id
        )

        order_row = Order.query.filter_by(
            id=payment.order_id, tenant_id=tenant_id
        ).first()
        marked_paid = False
        if order_row is not None and order_row.payment_status != "paid":
            self._orders.mark_paid(order_row)
            marked_paid = True
            publish("order.paid", order_id=order_row.id, tenant_id=tenant_id)

        db.session.commit()
        return {
            "processed": True,
            "payment": payment.to_dict(),
            "financial_event": event.to_dict(),
            "commission_ledger_id": ledger.id if ledger else None,
            "order_marked_paid": marked_paid,
        }
