"""Invoice rendering with Azadexa footer (wave 4 #46, §0.13.6)."""

from __future__ import annotations

import html
import re
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
        body_html, count = re.subn(
            r'(<footer[^>]*id="azadexa-platform-footer"[^>]*>).*?(</footer>)',
            lambda m: m.group(1) + footer_html + m.group(2),
            body_html,
            count=1,
            flags=re.S | re.I,
        )
        if not count:
            body_html += (
                '<footer id="azadexa-platform-footer" class="azadexa-platform-footer" '
                f'data-immutable="true">{footer_html}</footer>'
            )
        return body_html

    def render_invoice_html(
        self,
        *,
        order: Order,
        payment: Payment,
        template_row: TenantDocumentTemplate | None,
        footer_html: str,
    ) -> str:
        from core.i18n_messages import localize, request_locale
        from tenant.tenant_config import TenantConfig

        locale = request_locale()
        config = TenantConfig.query.filter_by(tenant_id=order.tenant_id).first()
        net = (
            Decimal(str(order.total)) - Decimal(str(order.tax_amount))
            if config and config.tax_included
            else Decimal(str(order.subtotal))
        )

        body = (
            template_row.body_html if template_row else None
        ) or default_invoice_body(locale)
        self.validate_template(body)
        esc = html.escape
        body = body.replace("{{order_number}}", esc(order.order_number or ""))
        body = body.replace("{{total}}", str(order.total))
        body = body.replace("{{customer_email}}", esc(order.customer_email or ""))
        body = body.replace("{{subtotal}}", str(net))
        body = body.replace("{{tax_amount}}", str(order.tax_amount))
        tax_block = (
            "<p class='tax-summary'>"
            + localize("المجموع قبل الضريبة", "Net of tax", locale)
            + f": {net} · "
            + localize("الضريبة", "Tax", locale)
            + f": {order.tax_amount} {payment.currency}</p>"
        )
        # Place the tax summary BEFORE the footer: inject_platform_footer
        # rewrites the whole footer span, so a block inserted inside it would
        # be silently removed from the rendered invoice.
        if re.search(r"<footer\b", body, re.I):
            body = re.sub(
                r"<footer\b",
                lambda m: tax_block + m.group(0),
                body,
                count=1,
                flags=re.I,
            )
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
        commit: bool = True,
    ) -> Invoice:
        existing = Invoice.query.filter_by(
            tenant_id=order.tenant_id, order_id=order.id
        ).first()
        if existing is not None:
            return existing
        try:
            footer = PlatformSettingsService().get_singleton().footer_html
        except Exception:
            footer = ""
        from core.i18n_messages import request_locale
        from tenant.tenant_config import TenantConfig

        locale = request_locale()
        template_row = self.load_active_template(order.tenant_id, locale=locale)
        rendered = self.render_invoice_html(
            order=order,
            payment=payment,
            template_row=template_row,
            footer_html=footer,
        )
        pdf_bytes = html_to_pdf(rendered)
        invoice_number = f"INV-{order.tenant_id}-{uuid.uuid4().hex.upper()}"
        config = TenantConfig.query.filter_by(tenant_id=order.tenant_id).first()
        net = (
            Decimal(str(order.total)) - Decimal(str(order.tax_amount))
            if config and config.tax_included
            else Decimal(str(order.subtotal))
        )
        invoice = Invoice(
            tenant_id=order.tenant_id,
            order_id=order.id,
            financial_event_id=financial_event.id,
            payment_id=payment.id,
            document_template_id=template_row.id if template_row else None,
            invoice_number=invoice_number,
            subtotal=net,
            tax_amount=order.tax_amount,
            total_amount=order.total,
            commission_amount=financial_event.commission_amount or Decimal("0"),
            currency=payment.currency,
            platform_footer_applied=bool(footer and footer in rendered),
            rendered_html=rendered,
        )
        db.session.add(invoice)
        db.session.flush()
        storage_key = self._store_pdf_artifact(
            order.tenant_id, invoice_number, pdf_bytes
        )
        invoice.pdf_artifact_path = storage_key
        invoice.storage_key = storage_key
        if commit:
            db.session.commit()
        return invoice

    def footer_html(self) -> str:
        row = PlatformSettings.query.filter_by(singleton="1").first()
        return row.footer_html if row else ""
