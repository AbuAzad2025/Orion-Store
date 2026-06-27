"""Invoice rendering with Azadexa footer (wave 4 #46)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from order.order import Order
from orion.extensions import db
from payment.payment import Payment
from platform_models.financial_event import FinancialEvent
from platform_models.invoice import Invoice
from platform_models.platform_settings import PlatformSettings
from platform_svc.platform_settings_service import PlatformSettingsService


class DocumentRenderer:
    def generate_invoice(
        self,
        *,
        order: Order,
        payment: Payment,
        financial_event: FinancialEvent,
    ) -> Invoice:
        settings = PlatformSettingsService().get_singleton()
        footer = settings.footer_html
        invoice = Invoice(
            tenant_id=order.tenant_id,
            order_id=order.id,
            financial_event_id=financial_event.id,
            payment_id=payment.id,
            invoice_number=f"INV-{order.tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            total_amount=order.total,
            commission_amount=financial_event.commission_amount or Decimal("0"),
            currency=payment.currency,
            platform_footer_applied=bool(footer),
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice

    def footer_html(self) -> str:
        row = PlatformSettings.query.filter_by(singleton="1").first()
        return row.footer_html if row else ""
