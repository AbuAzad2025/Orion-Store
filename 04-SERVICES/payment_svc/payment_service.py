"""Payment orchestrator (wave 4 #43)."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from currency_svc.currency_service import resolve_currency_for_tenant

from core.events import publish
from core.exceptions import ConflictError, NotFoundError, ValidationError
from integrations.payments._http import live_calls_enabled
from integrations.payments.bnpl import charge_bnpl
from integrations.payments.bnpl import refund_payment as refund_bnpl
from integrations.payments.palpay import charge_palpay
from integrations.payments.palpay import refund_payment as refund_palpay
from integrations.payments.paypal import charge_paypal
from integrations.payments.paypal import refund_payment as refund_paypal
from integrations.payments.stripe_connect import charge_stripe
from integrations.payments.stripe_connect import refund_payment as refund_stripe
from order.order import Order
from order_svc.order_service import OrderService
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from platform_svc.commission_service import CommissionService
from platform_svc.document_renderer import DocumentRenderer
from platform_svc.financial_events_service import FinancialEventsService
from tenant_gateway_svc.gateway_service import GatewayService

BNPL_GATEWAY_PREFIX = "bnpl_"


class PaymentService:
    def __init__(self) -> None:
        self._orders = OrderService()
        self._gateways = GatewayService()
        self._financial = FinancialEventsService()
        self._commission = CommissionService()
        self._documents = DocumentRenderer()
        self._bnpl = None

    def _bnpl_service(self):
        if self._bnpl is None:
            from bnpl_svc.bnpl_service import BnplService

            self._bnpl = BnplService()
        return self._bnpl

    def pay_order(
        self,
        *,
        tenant_id: int,
        order_public_id: str,
        payment_method: str = "cod",
    ) -> dict:
        order = self._orders.get_by_public_id(tenant_id, order_public_id)
        prior = (
            Payment.query.filter_by(tenant_id=tenant_id, order_id=order.id)
            .order_by(Payment.id.desc())
            .first()
        )
        if prior is not None:
            if prior.status in ("completed", "refunded"):
                raise ValidationError("Order already paid.")
            if prior.status in ("pending", "processing"):
                # A pending payment — including an uncertain network timeout —
                # must never start a second charge.
                raise ConflictError("Payment already in progress.")
        self._validate_payment_request(order)
        if payment_method == "cod":
            gateway = self._gateways.ensure_cod_gateway(tenant_id)
        else:
            gateway = self._gateways.get_enabled(tenant_id, payment_method)
        payment = self._create_payment_record(order, gateway.provider, payment_method)
        charge = self._charge_external_gateway(order, gateway, payment)
        if not charge.get("success"):
            if charge.get("uncertain"):
                # The provider may have charged before the connection broke.
                # Keep it pending so retries cannot start a second charge.
                payment.status = "pending"
            else:
                payment.status = "failed"
            db.session.commit()
            if charge.get("uncertain"):
                raise ConflictError("Payment result uncertain; reconcile before retry.")
            raise ValidationError(charge.get("error", "Payment failed."))
        payment.provider_payment_id = charge.get("provider_payment_id")
        payment.status = "completed"
        db.session.commit()
        event_type = charge.get("event_type", "order.payment")
        return self._on_payment_success(
            order, payment, event_type=event_type, bnpl_txn=charge.get("bnpl_txn")
        )

    def refund(
        self,
        *,
        tenant_id: int,
        payment_public_id: str,
        amount: Decimal | None = None,
        reason: str | None = None,
    ) -> dict:
        import uuid

        try:
            pid = uuid.UUID(payment_public_id)
        except ValueError as exc:
            raise NotFoundError("Payment not found.") from exc
        payment = Payment.query.filter_by(tenant_id=tenant_id, public_id=pid).first()
        if not payment:
            raise NotFoundError("Payment not found.")
        if payment.status != "completed":
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

        # A payment with an active (completed or pending) refund must never be
        # sent to the provider a second time. This is the double-refund guard.
        prior = (
            Refund.query.filter_by(payment_id=payment.id)
            .filter(Refund.status.in_(("pending", "completed")))
            .first()
        )
        if prior is not None:
            raise ConflictError("Payment already refunded.")

        result = self._refund_external_gateway(tenant_id, payment, refund_amount)
        if not result.get("success"):
            if result.get("uncertain"):
                # The provider may have refunded before the connection broke.
                # Persist a pending marker so a retry cannot double-refund.
                pending = Refund(
                    tenant_id=tenant_id,
                    payment_id=payment.id,
                    amount=refund_amount,
                    currency=payment.currency,
                    status="pending",
                    reason=reason,
                    provider_refund_id=None,
                )
                db.session.add(pending)
                db.session.commit()
                raise ConflictError("Refund result uncertain; reconcile before retry.")
            raise ValidationError(result.get("error", "Refund failed."))

        refund_row = Refund(
            tenant_id=tenant_id,
            payment_id=payment.id,
            amount=refund_amount,
            currency=payment.currency,
            status="completed",
            reason=reason,
            provider_refund_id=result.get("provider_refund_id"),
        )
        db.session.add(refund_row)
        db.session.flush()
        outbound = self._financial.record_outbound(
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
        # A refund reverses the original commission; it must not create a new one.
        ledger = None
        # A full refund closes the payment; a partial one keeps it completed while
        # the active Refund row still blocks any second refund attempt.
        if refund_amount >= Decimal(str(payment.amount)):
            payment.status = "refunded"
        db.session.commit()
        publish(
            "payment.refunded",
            order_id=payment.order_id,
            tenant_id=tenant_id,
            refund_id=refund_row.id,
            provider_refund_id=refund_row.provider_refund_id,
        )
        return {
            "refund": {
                "id": refund_row.id,
                "amount": str(refund_row.amount),
                "status": refund_row.status,
                "provider_refund_id": refund_row.provider_refund_id,
            },
            "financial_event": outbound.to_dict(),
            "commission_ledger_id": ledger.id if ledger else None,
            "provider_refund_id": refund_row.provider_refund_id,
            "uncertain": False,
        }

    def record_external_refund(self, **kwargs) -> dict:
        from payment_svc.external_refund_service import record_external_refund

        return record_external_refund(**kwargs)

    def _validate_payment_request(self, order: Order) -> None:
        if order.payment_status == "paid":
            raise ValidationError("Order already paid.")
        if order.status not in ("pending", "awaiting_payment"):
            raise ValidationError("Order is not payable.")

    def _create_payment_record(
        self, order: Order, provider: str, method: str
    ) -> Payment:
        payment = Payment(
            tenant_id=order.tenant_id,
            order_id=order.id,
            amount=order.total,
            currency=resolve_currency_for_tenant(order.tenant_id),
            payment_method=method,
            payment_provider=provider,
            status="pending",
        )
        db.session.add(payment)
        db.session.commit()
        return payment

    def _charge_external_gateway(self, order: Order, gateway, payment: Payment) -> dict:
        if gateway.provider == "cod":
            return {"success": True, "provider_payment_id": f"cod_{payment.id}"}
        if gateway.provider == "stripe":
            return charge_stripe(
                order=order,
                gateway=gateway,
                amount=Decimal(str(payment.amount)),
                currency=payment.currency,
            )
        if gateway.provider == "paypal":
            return charge_paypal(
                order=order,
                gateway=gateway,
                amount=Decimal(str(payment.amount)),
                currency=payment.currency,
            )
        if gateway.provider == "palpay":
            return charge_palpay(
                order=order,
                gateway=gateway,
                amount=Decimal(str(payment.amount)),
                currency=payment.currency,
            )
        if gateway.provider.startswith(BNPL_GATEWAY_PREFIX):
            provider_code = gateway.provider[len(BNPL_GATEWAY_PREFIX) :]
            bnpl_row = self._bnpl_service().get_enabled(order.tenant_id, provider_code)
            result = charge_bnpl(
                order=order,
                provider_row=bnpl_row,
                amount=Decimal(str(payment.amount)),
                currency=payment.currency,
            )
            if not result.get("success"):
                return result
            txn = self._bnpl_service().create_transaction(
                tenant_id=order.tenant_id,
                order_id=order.id,
                provider=provider_code,
                external_id=result["external_transaction_id"],
                amount=Decimal(str(payment.amount)),
                installment_plan=result.get("installment_plan"),
            )
            db.session.commit()
            return {
                "success": True,
                "provider_payment_id": result["external_transaction_id"],
                "event_type": "bnpl_capture",
                "bnpl_txn": txn,
            }
        return {"success": False, "error": "unsupported_provider"}

    def _refund_external_gateway(
        self, tenant_id: int, payment: Payment, amount: Decimal
    ) -> dict:
        """Dispatch a refund to the provider that originally captured the payment."""
        provider = payment.payment_provider
        if provider == "cod":
            return {
                "success": True,
                "provider_refund_id": f"cod_refund_{payment.id}",
                "uncertain": False,
            }
        gateway_fn = {
            "stripe": refund_stripe,
            "paypal": refund_paypal,
            "palpay": refund_palpay,
        }.get(provider)
        if gateway_fn is not None:
            gateway = self._refund_gateway(tenant_id, provider)
            return gateway_fn(
                payment=payment,
                gateway=gateway,
                amount=amount,
                currency=payment.currency,
            )
        if provider.startswith(BNPL_GATEWAY_PREFIX):
            code = provider[len(BNPL_GATEWAY_PREFIX) :]
            if live_calls_enabled():
                provider_row = self._bnpl_service().get_enabled(tenant_id, code)
            else:
                provider_row = SimpleNamespace(
                    tenant_id=tenant_id,
                    provider=code,
                    is_enabled=True,
                    config={"is_sandbox": True},
                    credentials_encrypted=None,
                    api_credentials_encrypted=None,
                )
            return refund_bnpl(
                payment=payment,
                provider_row=provider_row,
                amount=amount,
                currency=payment.currency,
            )
        return {
            "success": False,
            "provider_refund_id": None,
            "uncertain": False,
            "error": "unsupported_provider",
        }

    def _refund_gateway(self, tenant_id: int, provider: str):
        """Return the stored gateway row, or a sandbox placeholder in stub mode."""
        try:
            return self._gateways.get_enabled(tenant_id, provider)
        except NotFoundError:
            if live_calls_enabled():
                raise
            # Local/test stubs need no stored gateway row or credentials.
            return SimpleNamespace(
                tenant_id=tenant_id,
                provider=provider,
                display_name=provider,
                is_enabled=True,
                is_sandbox=True,
                status="active",
                config={},
                credentials_encrypted=None,
                api_credentials_encrypted=None,
            )

    def _on_payment_success(
        self,
        order: Order,
        payment: Payment,
        *,
        event_type: str = "order.payment",
        bnpl_txn=None,
    ) -> dict:
        event = self._financial.record_inbound(
            tenant_id=order.tenant_id,
            amount=payment.amount,
            event_type=event_type,
            source_entity="payment",
            source_id=payment.id,
            currency=payment.currency,
        )
        payment.financial_event_id = event.id
        ledger = self._commission.apply_from_event(
            event, payment_id=payment.id, order_id=order.id
        )
        order = self._orders.mark_paid(order)
        invoice = self._documents.generate_invoice(
            order=order, payment=payment, financial_event=event
        )
        publish("order.paid", order_id=order.id, tenant_id=order.tenant_id)
        payload = {
            "payment": payment.to_dict(),
            "order": order.to_dict(),
            "financial_event": event.to_dict(),
            "commission_ledger_id": ledger.id if ledger else None,
            "invoice": invoice.to_dict(),
        }
        if bnpl_txn is not None:
            payload["bnpl_transaction"] = bnpl_txn.to_dict()
        return payload
