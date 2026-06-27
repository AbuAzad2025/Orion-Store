"""Payment orchestrator (wave 4 #43)."""

from __future__ import annotations

from decimal import Decimal

from core.events import publish
from core.exceptions import ValidationError
from integrations.payments.stripe_connect import charge_stripe
from order.order import Order
from order_svc.order_service import OrderService
from orion.extensions import db
from payment.payment import Payment
from platform_svc.commission_service import CommissionService
from platform_svc.document_renderer import DocumentRenderer
from platform_svc.financial_events_service import FinancialEventsService
from tenant_gateway_svc.gateway_service import GatewayService


class PaymentService:
    def __init__(self) -> None:
        self._orders = OrderService()
        self._gateways = GatewayService()
        self._financial = FinancialEventsService()
        self._commission = CommissionService()
        self._documents = DocumentRenderer()

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
        return self._on_payment_success(order, payment)

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
        return {"success": False, "error": "unsupported_provider"}

    def _on_payment_success(self, order: Order, payment: Payment) -> dict:
        event = self._financial.record_inbound(
            tenant_id=order.tenant_id,
            amount=payment.amount,
            event_type="order.payment",
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
        return {
            "payment": payment.to_dict(),
            "order": order.to_dict(),
            "financial_event": event.to_dict(),
            "commission_ledger_id": ledger.id if ledger else None,
            "invoice": invoice.to_dict(),
        }
