"""Round-14: WhatsApp VAT snapshot + refund audit on an in-memory DB."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from catalog_svc.product_service import ProductService
from order_svc.whatsapp_order_service import WhatsAppOrderService
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from payment_svc.payment_service import PaymentService
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_models.financial_event import FinancialEvent
from platform_models.invoice import Invoice
from platform_svc import document_renderer
from platform_svc.pdf_service import InvoiceStorage, set_invoice_storage
from tenant.tenant import Tenant
from tenant_svc.tenant_service import TenantService

GROSS = Decimal("118.00")
NET = Decimal("100.00")
VAT = Decimal("18.00")
RATE = Decimal("0.18")


@pytest.fixture(autouse=True)
def _guard_not_live_db(database_url: str) -> None:
    url = database_url.lower()
    assert ":memory:" in url or "test" in url, f"non-test DB: {database_url!r}"


class _MemoryInvoiceStorage(InvoiceStorage):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        self.objects[key] = bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self.objects[key]


@pytest.fixture
def invoice_storage(monkeypatch):
    storage = _MemoryInvoiceStorage()
    set_invoice_storage(storage)
    monkeypatch.setattr(
        document_renderer, "html_to_pdf", lambda html: b"%PDF-1.7 in-memory"
    )
    yield storage
    set_invoice_storage(None)


@pytest.fixture
def vat_store(app):
    with app.app_context():
        tenant = TenantService().create_tenant(
            name="VAT WhatsApp Store",
            slug="vat-whatsapp-store",
            email="vat-whatsapp@test.com",
        )
        tenant.config.tax_rate = RATE
        tenant.config.tax_included = True
        db.session.commit()
        product = ProductService().create(
            tenant_id=tenant.id,
            name="VAT Inclusive Widget",
            slug="vat-inclusive-widget",
            price=str(GROSS),
            quantity=10,
            is_published=True,
        )
        return SimpleNamespace(tenant_id=tenant.id, product_id=product.id)


def _confirm_order(store):
    tenant = db.session.get(Tenant, store.tenant_id)
    svc = WhatsAppOrderService()
    order = svc.create(
        tenant,
        items=[{"product_id": store.product_id, "quantity": 1}],
        customer_name="Buyer",
        customer_email="buyer@test.com",
    )
    return svc.confirm(tenant_id=store.tenant_id, public_id=order.public_id)


def test_inclusive_order_snapshots_vat_on_invoice(app, vat_store, invoice_storage):
    with app.app_context():
        order = _confirm_order(vat_store)
        db.session.refresh(order)
        assert (
            order.subtotal == GROSS and order.tax_amount == VAT and order.total == GROSS
        )
        invoice = Invoice.query.filter_by(
            tenant_id=vat_store.tenant_id, order_id=order.id
        ).one()
        assert invoice.subtotal == NET
        assert invoice.tax_amount == VAT
        assert invoice.total_amount == GROSS
        assert "المجموع قبل الضريبة" in invoice.rendered_html
        assert invoice.storage_key.endswith(".pdf")
        assert invoice_storage.get(invoice.storage_key).startswith(b"%PDF")
        payment = Payment.query.filter_by(order_id=order.id).one()
        assert payment.payment_provider == "whatsapp"


def test_full_refund_keeps_vat_snapshot_and_passes_audit(
    app, vat_store, invoice_storage, monkeypatch
):
    import scripts.audit_financial_integrity as audit

    with app.app_context():
        order = _confirm_order(vat_store)
        invoice = Invoice.query.filter_by(
            tenant_id=vat_store.tenant_id, order_id=order.id
        ).one()
        payment = Payment.query.filter_by(order_id=order.id).one()
        inbound = db.session.get(FinancialEvent, payment.financial_event_id)
        result = PaymentService().refund(
            tenant_id=vat_store.tenant_id, payment_public_id=str(payment.public_id)
        )
        assert Decimal(str(result["refund"]["amount"])) == GROSS
        db.session.refresh(order)
        db.session.refresh(invoice)
        assert invoice.tax_amount == VAT and invoice.total_amount == GROSS
        refund = Refund.query.filter_by(payment_id=payment.id).one()
        outbound = db.session.get(FinancialEvent, refund.financial_event_id)
        assert outbound.amount == -GROSS
        assert outbound.metadata_json["reverses_financial_event_id"] == inbound.id
        reversal = PlatformCommissionLedger.query.filter_by(
            tenant_id=vat_store.tenant_id, entry_type="commission_reversal"
        ).one()
        assert (
            reversal.commission_amount < 0 and reversal.reverses_ledger_id is not None
        )

        records: list[tuple[str, bool, str]] = []

        def capture(name, ok, detail="", group=None):
            records.append((name, bool(ok), detail))

        monkeypatch.setattr(audit, "check", capture)
        monkeypatch.setattr("orion.app.create_app", lambda env: app)
        audit.FAILURES.clear()
        audit.CHECKS = 0
        audit.CHECK_RESULTS.clear()
        audit.main()
        assert records
        failures = [f"{n}: {d}" for n, ok, d in records if not ok]
        assert failures == [], failures


def test_partial_refund_does_not_recompute_vat(app, vat_store, invoice_storage):
    with app.app_context():
        order = _confirm_order(vat_store)
        invoice = Invoice.query.filter_by(
            tenant_id=vat_store.tenant_id, order_id=order.id
        ).one()
        payment = Payment.query.filter_by(order_id=order.id).one()
        result = PaymentService().refund(
            tenant_id=vat_store.tenant_id,
            payment_public_id=str(payment.public_id),
            amount=Decimal("59.00"),
            reason="partial return",
        )
        assert Decimal(str(result["refund"]["amount"])) == Decimal("59.00")
        db.session.refresh(order)
        db.session.refresh(invoice)
        db.session.refresh(payment)
        assert invoice.tax_amount == VAT
        assert payment.status == "completed"
