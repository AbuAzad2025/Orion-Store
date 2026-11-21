"""Commission reversal + tenant-scoped nightly reconciliation tests."""

from __future__ import annotations

from decimal import Decimal

from catalog_svc.product_service import ProductService
from core.events import publish
from orion.extensions import db
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from payment.payment import Payment
from payment.refund import Refund
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_svc.commission_service import CommissionService
from platform_svc.financial_events_service import FinancialEventsService
from platform_svc.platform_settings_service import PlatformSettingsService
from platform_svc.reconciliation_service import ReconciliationService
from tenant_svc.tenant_service import TenantService


def _order_for(tenant):
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Widget",
        slug=f"widget-{tenant.id}",
        price="50.00",
        quantity=10,
        is_published=True,
    )
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    return CheckoutService().checkout(
        cart=cart,
        customer_email="reversal@test.com",
        shipping_address={"city": "Ramallah"},
    )


def _seed_payment(label: str):
    PlatformSettingsService().ensure_seeded()
    tenant = TenantService().create_tenant(
        name=f"Rev {label}",
        slug=f"rev-{label}-store",
        email=f"rev-{label}@test.com",
    )
    order = _order_for(tenant)
    event = FinancialEventsService().record_inbound(
        tenant_id=tenant.id,
        amount="50.00",
        event_type="order.payment",
        source_entity="payment",
        source_id=1,
    )
    payment = Payment(
        tenant_id=tenant.id,
        order_id=order.id,
        financial_event_id=event.id,
        amount=Decimal("50.00"),
        currency="ILS",
        payment_method="card",
        payment_provider="test",
        status="completed",
    )
    db.session.add(payment)
    db.session.flush()
    ledger = CommissionService().apply_from_event(
        event, payment_id=payment.id, order_id=order.id
    )
    return tenant, order, payment, event, ledger


def _seed_refund(tenant, payment, original_event):
    refund = Refund(
        tenant_id=tenant.id,
        payment_id=payment.id,
        amount=payment.amount,
        currency="ILS",
        status="completed",
    )
    db.session.add(refund)
    db.session.flush()
    outbound = FinancialEventsService().record_outbound(
        tenant_id=tenant.id,
        amount=-payment.amount,
        event_type="payment.refund",
        source_entity="refund",
        source_id=refund.id,
        apply_commission=False,
        allow_negative=True,
        metadata={"reverses_financial_event_id": original_event.id},
    )
    refund.financial_event_id = outbound.id
    db.session.commit()
    return refund, outbound


def _reversals(tenant_id: int) -> list[PlatformCommissionLedger]:
    return (
        PlatformCommissionLedger.query.filter_by(
            tenant_id=tenant_id, entry_type="commission_reversal"
        )
        .order_by(PlatformCommissionLedger.id)
        .all()
    )


def test_reverse_event_creates_one_negative_reversal(app):
    tenant, _order, payment, event, original = _seed_payment("reverse")

    reversal = CommissionService().reverse(event)
    assert reversal is not None
    assert reversal.direction == "debit"
    assert reversal.entry_type == "commission_reversal"
    assert reversal.reverses_ledger_id == original.id
    assert reversal.gross_amount == Decimal("-50.00")
    assert reversal.commission_amount == Decimal("-0.50")
    assert reversal.payment_id == payment.id
    assert reversal.status == "settled"

    # Same event reversed again → must return the existing row, never duplicate.
    again = CommissionService().reverse(event)
    assert again is not None
    assert again.id == reversal.id
    assert len(_reversals(tenant.id)) == 1


def test_reverse_for_payment_is_idempotent(app):
    tenant, _order, payment, event, _original = _seed_payment("forpayment")
    _refund, _outbound = _seed_refund(tenant, payment, event)

    first = CommissionService().reverse_for_payment(tenant.id, payment.id)
    second = CommissionService().reverse_for_payment(tenant.id, payment.id)
    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert len(_reversals(tenant.id)) == 1

    # A different tenant cannot reverse this payment.
    other = TenantService().create_tenant(
        name="Other", slug="other-store", email="other@test.com"
    )
    assert CommissionService().reverse_for_payment(other.id, payment.id) is None


def test_refund_event_handler_reverses_commission(app):
    tenant, order, payment, event, _original = _seed_payment("handler")
    refund, _outbound = _seed_refund(tenant, payment, event)

    publish(
        "payment.refunded",
        order_id=order.id,
        tenant_id=tenant.id,
        refund_id=refund.id,
    )

    reversals = _reversals(tenant.id)
    assert len(reversals) == 1
    assert reversals[0].direction == "debit"


def test_reconciliation_skips_unconfirmed_event(app):
    tenant, _order, _payment, event, ledger = _seed_payment("unconfirmed")
    event.status = "pending"
    db.session.commit()

    settled = ReconciliationService().settle_pending_commissions(tenant_id=tenant.id)
    assert settled == 0
    db.session.expire_all()
    assert PlatformCommissionLedger.query.get(ledger.id).status == "pending"


def test_reconciliation_settles_only_one_tenant(app):
    tenant_a, _o1, _p1, _e1, ledger_a = _seed_payment("tenant-a")
    tenant_b, _o2, _p2, _e2, ledger_b = _seed_payment("tenant-b")

    settled = ReconciliationService().settle_pending_commissions(tenant_id=tenant_a.id)
    assert settled == 1

    db.session.expire_all()
    assert PlatformCommissionLedger.query.get(ledger_a.id).status == "settled"
    assert PlatformCommissionLedger.query.get(ledger_b.id).status == "pending"

    # Per-tenant result is recorded on the ledger note and via get_status.
    assert "matched tenant=" in (PlatformCommissionLedger.query.get(ledger_a.id).notes or "")
    status = ReconciliationService().get_status(tenant_id=tenant_b.id)
    assert status["pending_commission_entries"] == 1
