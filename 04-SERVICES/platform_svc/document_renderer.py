"""Invoice rendering with Azadexa footer (wave 4 #46, §0.13.6)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from core.exceptions import TemplateValidationError
from order.order import Order
from orion.extensions import db
from payment.payment import Payment
from platform_models.financial_event import FinancialEvent
from platform_models.invoice import Invoice, TenantDocumentTemplate
from platform_models.platform_settings import PlatformSettings
from platform_svc.pdf_service import get_invoice_storage, html_to_pdf
from platform_svc.platform_settings_service import PlatformSettingsService


def default_invoice_body(locale: str | None = None) -> str:
    from core.i18n_messages import localize

    heading = localize("فاتورة", "Invoice", locale)
    return (
        f'<div class="invoice-header"><h1>{heading}</h1></div>'
        '<div class="invoice-body">{{order_number}}</div>'
        '<footer id="azadexa-platform-footer" class="azadexa-platform-footer" '
        'data-immutable="true"></footer>'
    )


DEFAULT_INVOICE_BODY = default_invoice_body()


class DocumentRenderer:
    def validate_template(self, html: str) -> None:
        if "azadexa-platform-footer" not in html:
            raise TemplateValidationError("Footer placeholder required.")
        if 'data-immutable="true"' not in html:
            raise TemplateValidationError("Immutable footer marker required.")

    def load_active_template(
        self, tenant_id: int, document_type: str = "invoice", locale: str = "ar"
    ) -> TenantDocumentTemplate | None:
        return TenantDocumentTemplate.query.filter_by(
            tenant_id=tenant_id,
            document_type=document_type,
            locale=locale,
            is_active=True,
        ).first()

    def inject_platform_footer(self, body_html: str, footer_html: str) -> str:
        if "azadexa-platform-footer" not in body_html:
            body_html += (
                '<footer id="azadexa-platform-footer" class="azadexa-platform-footer" '
                f'data-immutable="true">{footer_html}</footer>'
            )
            return body_html
        return body_html.replace("></footer>", f">{footer_html}</footer>", 1)

    def render_invoice_html(
        self,
        *,
        order: Order,
        payment: Payment,
        template_row: TenantDocumentTemplate | None,
        footer_html: str,
    ) -> str:
        from core.i18n_messages import localize, request_locale

        locale = request_locale()

        body = (
            template_row.body_html if template_row else None
        ) or default_invoice_body(request_locale())
        self.validate_template(body)
        body = body.replace("{{order_number}}", order.order_number)
        body = body.replace("{{total}}", str(order.total))
        body = body.replace("{{customer_email}}", order.customer_email)
        body = body.replace("{{subtotal}}", str(order.subtotal))
        body = body.replace("{{tax_amount}}", str(order.tax_amount))
        tax_block = (
            "<p class='tax-summary'>"
            + localize("المجموع قبل الضريبة", "Subtotal")
            + f": {order.subtotal} · "
            + localize("الضريبة", "Tax")
            + f": {order.tax_amount} {payment.currency}"
            + "</p>"
        )
        if "</footer>" in body:
            body = body.replace("</footer>", tax_block + "</footer>", 1)
        else:
            body += tax_block
        return self.inject_platform_footer(body, footer_html)

    def _store_pdf_artifact(
        self, tenant_id: int, invoice_number: str, pdf: bytes
    ) -> str:
        """Persist the PDF through the configured object storage backend.

        The returned key is what Invoice.storage_key records; callers resolve
        bytes back through ``get_invoice_storage().get(key)``.
        """
        key = f"{tenant_id}/{invoice_number}.pdf"
        return get_invoice_storage().put(key, pdf)

    def generate_invoice(
        self,
        *,
        order: Order,
        payment: Payment,
        financial_event: FinancialEvent,
    ) -> Invoice:
        settings = PlatformSettingsService().get_singleton()
        footer = settings.footer_html
        template_row = self.load_active_template(order.tenant_id)
        rendered = self.render_invoice_html(
            order=order,
            payment=payment,
            template_row=template_row,
            footer_html=footer,
        )
        pdf_bytes = html_to_pdf(rendered)
        invoice_number = f"INV-{order.tenant_id}-{uuid.uuid4().hex[:8].upper()}"
        storage_key = self._store_pdf_artifact(
            order.tenant_id, invoice_number, pdf_bytes
        )
        invoice = Invoice(
            tenant_id=order.tenant_id,
            order_id=order.id,
            financial_event_id=financial_event.id,
            payment_id=payment.id,
            document_template_id=template_row.id if template_row else None,
            invoice_number=invoice_number,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            total_amount=order.total,
            commission_amount=financial_event.commission_amount or Decimal("0"),
            currency=payment.currency,
            platform_footer_applied=bool(footer),
            rendered_html=rendered,
            pdf_artifact_path=storage_key,
            storage_key=storage_key,
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice

    def footer_html(self) -> str:
        row = PlatformSettings.query.filter_by(singleton="1").first()
        return row.footer_html if row else ""
