"""Payment orchestrator (wave 4 #43)."""

from __future__ import annotations

from decimal import Decimal

from core.events import publish
from core.exceptions import NotFoundError, ValidationError
from integrations.payments.bnpl import charge_bnpl
from integrations.payments.palpay import charge_palpay
from integrations.payments.paypal import charge_paypal
from integrations.payments.stripe_connect import charge_stripe
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
        self._validate_payment_request(order)
        if payment_method == "cod":
            gateway = self._gateways.ensure_cod_gateway(tenant_id)
        else:
            gateway = self._gateways.get_enabled(tenant_id, payment_method)
        payment = self._create_payment_record(order, gateway.provider, payment_method)
        charge = self._charge_external_gateway(order, gateway, payment)
        if not charge.get("success"):
            payment.status = "failed"
            db.session.commit()
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
        refund_row = Refund(
            tenant_id=tenant_id,
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            status="completed",
            reason=reason,
        )
        db.session.add(refund_row)
        db.session.flush()
        outbound = self._financial.record_outbound(
            tenant_id=tenant_id,
            amount=payment.amount,
            event_type="payment.refund",
            source_entity="refund",
            source_id=refund_row.id,
        )
        refund_row.financial_event_id = outbound.id
        ledger = self._commission.apply_from_event(
            outbound, payment_id=payment.id, order_id=payment.order_id
        )
        payment.status = "refunded"
        db.session.commit()
        publish(
            "payment.refunded",
            order_id=payment.order_id,
            tenant_id=tenant_id,
            refund_id=refund_row.id,
        )
        return {
            "refund": {
                "id": refund_row.id,
                "amount": str(refund_row.amount),
                "status": refund_row.status,
            },
            "financial_event": outbound.to_dict(),
            "commission_ledger_id": ledger.id if ledger else None,
        }

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
            currency="ILS",
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
                order=order, gateway=gateway, amount=Decimal(str(payment.amount))
            )
        if gateway.provider == "paypal":
            return charge_paypal(
                order=order, gateway=gateway, amount=Decimal(str(payment.amount))
            )
        if gateway.provider == "palpay":
            return charge_palpay(
                order=order, gateway=gateway, amount=Decimal(str(payment.amount))
            )
        if gateway.provider.startswith(BNPL_GATEWAY_PREFIX):
            provider_code = gateway.provider[len(BNPL_GATEWAY_PREFIX) :]
            bnpl_row = self._bnpl_service().get_enabled(order.tenant_id, provider_code)
            result = charge_bnpl(
                order=order,
                provider_row=bnpl_row,
                amount=Decimal(str(payment.amount)),
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
