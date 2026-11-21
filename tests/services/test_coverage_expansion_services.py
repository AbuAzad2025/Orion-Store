"""Real-DB tests that expand coverage of low-coverage service modules.

Covers create/list/update/complete/error paths that the existing suite does not
exercise. All persistence goes through the real PostgreSQL test database; no
core logic or ORM session is mocked.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from affiliate.affiliate import AffiliateCommission, AffiliateLink
from affiliate_svc.affiliate_service import AffiliateService
from bopis.bopis import PickupLocation, PickupSlot
from bopis_svc.bopis_service import BopisService
from bundle.bundle import BundleItem
from bundle_svc.bundle_service import BundleService
from catalog.product import Product
from core.exceptions import ConflictError, NotFoundError, ValidationError
from core.utils import utc_now
from feature_flag.feature_flag import FeatureFlag, TenantFeatureFlagOverride
from feature_flag_svc.feature_flag_service import FeatureFlagService
from fraud.fraud import Chargeback, FraudReview, FraudRule
from fraud_svc.fraud_service import FraudService, on_order_created
from import_export.import_export import ImportExportJob
from import_export_svc.import_export_service import ImportExportService
from order.order import Order, OrderItem
from orion.extensions import db
from payment.payment import Payment
from payment.refund import Refund
from payment_svc.external_refund_service import record_external_refund
from platform_models.commission_ledger import PlatformCommissionLedger
from platform_models.financial_event import FinancialEvent
from platform_svc.commission_service import CommissionService
from platform_svc.financial_events_service import FinancialEventsService
from subscription.subscription import (
    CustomerSubscription,
    DigitalAsset,
    DigitalDownload,
    LicenseKey,
    SubscriptionEvent,
)
from subscription_svc.subscription_service import SubscriptionService
from tenant_svc.tenant_service import TenantService
from user.user import User


def _token() -> str:
    return uuid.uuid4().hex[:10]


# ---------------------------------------------------------------------------
# Shared real-DB fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant(app):
    token = _token()
    return TenantService().create_tenant(
        name=f"Coverage Store {token}",
        slug=f"cov-{token}",
        email=f"cov-{token}@test.com",
    )


@pytest.fixture
def product(tenant):
    prod = Product(
        tenant_id=tenant.id,
        name="Widget",
        slug=f"widget-{_token()}",
        price="29.99",
        quantity=100,
        is_published=True,
    )
    db.session.add(prod)
    db.session.commit()
    return prod


def _order(tenant_id: int, *, total: str = "100.00", email: str | None = None, **kw):
    order = Order(
        tenant_id=tenant_id,
        order_number=f"COV-{_token()}",
        customer_email=email or f"buyer-{_token()}@test.com",
        shipping_address={},
        subtotal=total,
        total=total,
        **kw,
    )
    db.session.add(order)
    db.session.commit()
    return order


def _user(tenant_id: int) -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"reviewer-{_token()}@test.com",
        password_hash="not-a-real-hash",
        is_admin=True,
        is_customer=False,
        first_name="Reviewer",
    )
    db.session.add(user)
    db.session.commit()
    return user


def _payment(
    tenant_id: int,
    order_id: int,
    *,
    amount: str = "100.00",
    status: str = "completed",
    with_event: bool = True,
):
    event = None
    if with_event:
        event = FinancialEventsService().record_inbound(
            tenant_id=tenant_id,
            amount=amount,
            event_type="order.payment",
            source_entity="order",
            source_id=order_id,
        )
    payment = Payment(
        tenant_id=tenant_id,
        order_id=order_id,
        financial_event_id=event.id if event else None,
        amount=Decimal(amount),
        currency="ILS",
        payment_method="card",
        payment_provider="test",
        status=status,
    )
    db.session.add(payment)
    db.session.commit()
    return payment, event


def _refund_with_event(tenant_id: int, payment, *, amount: str, metadata: dict | None):
    refund = Refund(
        tenant_id=tenant_id,
        payment_id=payment.id,
        amount=Decimal(amount),
        currency="ILS",
        status="completed",
    )
    db.session.add(refund)
    db.session.flush()
    outbound = FinancialEventsService().record_outbound(
        tenant_id=tenant_id,
        amount=-Decimal(amount),
        event_type="payment.refund",
        source_entity="refund",
        source_id=refund.id,
        apply_commission=False,
        allow_negative=True,
        metadata=metadata,
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


# ---------------------------------------------------------------------------
# bundle_svc.bundle_service
# ---------------------------------------------------------------------------


def test_bundle_add_item_list_and_resolve_price(app, db_session, tenant, product):
    svc = BundleService()
    bundle = svc.create_bundle(
        tenant_id=tenant.id, name="Combo", slug=f"combo-{_token()}", bundle_price="5.00"
    )

    with pytest.raises(NotFoundError):
        svc.add_item(
            tenant_id=tenant.id,
            bundle_id=999_999,
            product_id=product.id,
        )

    discounted = svc.add_item(
        tenant_id=tenant.id,
        bundle_id=bundle.id,
        product_id=product.id,
        quantity=2,
        discount_percent="10",
    )
    plain = svc.add_item(
        tenant_id=tenant.id,
        bundle_id=bundle.id,
        product_id=product.id,
    )
    assert discounted.quantity == 2
    assert discounted.discount_percent == Decimal("10.00")
    assert plain.quantity == 1
    assert plain.discount_percent == Decimal("0.00")
    assert BundleItem.query.filter_by(bundle_id=bundle.id).count() == 2

    # Empty bundles resolve to zero; items use real product prices, quantity and
    # per-item discount.
    empty = svc.create_bundle(
        tenant_id=tenant.id,
        name="Empty",
        slug=f"empty-{_token()}",
        bundle_price="0",
    )
    assert svc.resolve_bundle_price(empty) == Decimal("0")
    expected = Decimal("29.99") * Decimal("0.9") * 2 + Decimal("29.99")
    assert svc.resolve_bundle_price(bundle) == pytest.approx(expected)

    assert {b.id for b in svc.list_bundles(tenant.id)} == {bundle.id, empty.id}
    assert svc.list_bundles(tenant.id + 1000) == []


# ---------------------------------------------------------------------------
# import_export_svc.import_export_service
# ---------------------------------------------------------------------------


def test_import_export_progress_and_ordering(app, db_session, tenant):
    svc = ImportExportService()
    first = svc.create_job(
        tenant_id=tenant.id,
        job_type="import",
        entity_type="products",
        file_url="https://example.test/products.csv",
    )
    first.created_at = utc_now() - timedelta(days=1)
    db_session.commit()
    second = svc.create_job(
        tenant_id=tenant.id,
        job_type="export",
        entity_type="orders",
        user_id=None,
    )
    assert first.status == "pending" and second.status == "pending"

    assert [job.id for job in svc.list_jobs(tenant.id)] == [second.id, first.id]
    assert svc.list_jobs(tenant.id + 1000) == []

    in_progress = svc.update_progress(
        job_id=second.id,
        tenant_id=tenant.id,
        processed=2,
        failed=1,
        total=10,
    )
    assert in_progress.status == "pending"
    assert (in_progress.processed_count, in_progress.failed_count) == (2, 1)
    assert in_progress.total_count == 10

    completed = svc.update_progress(
        job_id=second.id, tenant_id=tenant.id, processed=10, failed=0, total=10
    )
    assert completed.status == "completed"
    assert completed.id == in_progress.id

    with_errors = svc.update_progress(
        job_id=second.id, tenant_id=tenant.id, processed=8, failed=2, total=10
    )
    assert with_errors.status == "completed_with_errors"
    assert ImportExportJob.query.filter_by(id=second.id).one().status == (
        "completed_with_errors"
    )

    with pytest.raises(NotFoundError):
        svc.update_progress(job_id=999_999, tenant_id=tenant.id)


# ---------------------------------------------------------------------------
# affiliate_svc.affiliate_service
# ---------------------------------------------------------------------------


def test_affiliate_registration_commissions_and_links(app, db_session, tenant, product):
    svc = AffiliateService()
    program = svc.create_program(
        tenant_id=tenant.id,
        name="Gold Partners",
        code="  GOLD  ",
        commission_type="percentage",
        commission_value="15.00",
        cookie_days=15,
    )
    assert program.code == "gold"
    assert program.cookie_days == 15

    with pytest.raises(NotFoundError):
        svc.register_affiliate(
            tenant_id=tenant.id, program_id=999_999, email="nobody@test.com"
        )

    affiliate = svc.register_affiliate(
        tenant_id=tenant.id,
        program_id=program.id,
        email="  Affiliate@Example.COM  ",
    )
    assert affiliate.email == "affiliate@example.com"
    assert len(affiliate.referral_code) == 8

    order = _order(tenant.id)
    commission = svc.record_commission(
        tenant_id=tenant.id,
        affiliate_id=affiliate.id,
        order_id=order.id,
        amount="12.50",
    )
    assert commission.amount == Decimal("12.50")
    assert commission.status == "pending"
    assert (
        AffiliateCommission.query.filter_by(affiliate_id=affiliate.id).one().id
        == commission.id
    )

    link = svc.create_link(
        affiliate_id=affiliate.id,
        url="https://example.test/p/1",
        product_id=product.id,
    )
    assert link.tenant_id == tenant.id
    assert link.product_id == product.id
    assert link.click_count == 0

    simple_link = svc.create_link(
        affiliate_id=affiliate.id, url="https://example.test/home"
    )
    assert simple_link.product_id is None
    assert AffiliateLink.query.filter_by(affiliate_id=affiliate.id).count() == 2

    with pytest.raises(NotFoundError):
        svc.create_link(affiliate_id=999_999, url="https://example.test/missing")


# ---------------------------------------------------------------------------
# bopis_svc.bopis_service
# ---------------------------------------------------------------------------


def test_bopis_slot_booking_and_active_listing(app, db_session, tenant):
    svc = BopisService()
    location = svc.create_location(
        tenant_id=tenant.id,
        code=f"DTLA-{_token()}",
        name="Downtown Store",
        address={"city": "LA"},
    )
    inactive = PickupLocation(
        tenant_id=tenant.id,
        code=f"INACTIVE-{_token()}",
        name="Closed Store",
        address={},
        is_active=False,
    )
    db.session.add(inactive)
    db.session.commit()
    assert [loc.id for loc in svc.list_locations(tenant.id)] == [location.id]
    assert svc.list_locations(tenant.id + 1000) == []

    today = datetime.utcnow().weekday()
    slot = svc.create_slot(
        location_id=location.id,
        tenant_id=tenant.id,
        day_of_week=today,
        start_time="09:00",
        end_time="17:00",
        max_orders=1,
    )
    assert slot.current_orders == 0 and slot.max_orders == 1
    assert PickupSlot.query.filter_by(id=slot.id).one().is_active is True

    order = _order(tenant.id)
    booking = svc.book_checkout(
        location_id=location.id, tenant_id=tenant.id, order_id=order.id
    )
    assert booking == {
        "location_id": location.id,
        "slot_id": slot.id,
        "day_of_week": today,
        "start_time": "09:00",
        "end_time": "17:00",
    }
    assert PickupSlot.query.filter_by(id=slot.id).one().current_orders == 1

    with pytest.raises(ValidationError, match="full"):
        svc.book_checkout(
            location_id=location.id, tenant_id=tenant.id, order_id=order.id
        )

    other = svc.create_location(
        tenant_id=tenant.id,
        code=f"OTHER-{_token()}",
        name="No Slots Store",
        address={},
    )
    svc.create_slot(
        location_id=other.id,
        tenant_id=tenant.id,
        day_of_week=(today + 1) % 7,
        start_time="09:00",
        end_time="17:00",
    )
    with pytest.raises(ValidationError, match="No pickup slot available today"):
        svc.book_checkout(location_id=other.id, tenant_id=tenant.id, order_id=order.id)


# ---------------------------------------------------------------------------
# subscription_svc.subscription_service
# ---------------------------------------------------------------------------


def test_subscription_trial_cancel_and_listing(app, db_session, tenant):
    svc = SubscriptionService()
    active = svc.create_plan(
        tenant_id=tenant.id,
        name="Pro",
        code="  PRO  ",
        billing_period_days=30,
        price="29.99",
    )
    trial = svc.create_plan(
        tenant_id=tenant.id,
        name="Trial",
        code="trial",
        billing_period_days=30,
        price="0",
        trial_period_days=14,
    )
    archived = svc.create_plan(
        tenant_id=tenant.id,
        name="Old",
        code="old",
        billing_period_days=30,
        price="1",
    )
    archived.is_active = False
    db_session.commit()
    assert active.code == "pro"
    assert {p.id for p in svc.list_plans(tenant.id)} == {active.id, trial.id}

    with pytest.raises(NotFoundError):
        svc.subscribe(tenant_id=tenant.id, plan_id=999_999, customer_email="x@test.com")

    sub = svc.subscribe(
        tenant_id=tenant.id,
        plan_id=trial.id,
        customer_email="  TRIAL@Example.com ",
        user_id=None,
    )
    assert sub.status == "trialing"
    assert sub.customer_email == "trial@example.com"
    assert sub.trial_end is not None
    assert sub.current_period_end > sub.current_period_start
    created = SubscriptionEvent.query.filter_by(
        subscription_id=sub.id, event_type="subscription.created"
    ).one()
    assert "Trial" in (created.message or "")

    plain = svc.subscribe(
        tenant_id=tenant.id, plan_id=active.id, customer_email="pro@test.com"
    )
    assert plain.status == "active" and plain.trial_end is None
    assert {s.id for s in svc.list_subscriptions(tenant.id)} == {sub.id, plain.id}
    assert svc.list_subscriptions(tenant.id + 1000) == []

    with pytest.raises(NotFoundError):
        svc.cancel(tenant_id=tenant.id, subscription_id=999_999)

    cancelled = svc.cancel(tenant_id=tenant.id, subscription_id=sub.id)
    assert cancelled.status == "cancelled" and cancelled.cancelled_at is not None
    assert CustomerSubscription.query.filter_by(id=sub.id).one().status == "cancelled"
    assert (
        SubscriptionEvent.query.filter_by(
            subscription_id=sub.id, event_type="subscription.cancelled"
        ).count()
        == 1
    )


def test_subscription_digital_assets_downloads_and_license(
    app, db_session, tenant, product
):
    svc = SubscriptionService()
    asset = svc.create_digital_asset(
        tenant_id=tenant.id,
        product_id=product.id,
        file_url="https://example.test/ebook.pdf",
        file_name="ebook.pdf",
        mime_type="application/pdf",
        max_downloads=3,
    )
    assert asset.file_name == "ebook.pdf" and asset.max_downloads == 3
    assert DigitalAsset.query.filter_by(id=asset.id).one().mime_type == (
        "application/pdf"
    )

    with pytest.raises(NotFoundError):
        svc.create_download(
            tenant_id=tenant.id, asset_id=999_999, order_id=_order(tenant.id).id
        )

    order = _order(tenant.id)
    download = svc.create_download(
        tenant_id=tenant.id, asset_id=asset.id, order_id=order.id
    )
    assert download.asset_id == asset.id and download.order_id == order.id
    assert len(download.download_token) == 32
    assert download.expires_at > utc_now() + timedelta(days=29)
    assert DigitalDownload.query.filter_by(id=download.id).one().download_count == 0

    item = OrderItem(
        tenant_id=tenant.id,
        order_id=order.id,
        product_id=product.id,
        product_name="Widget",
        unit_price="29.99",
        quantity=1,
        total_price="29.99",
    )
    db.session.add(item)
    db.session.commit()
    licence = svc.generate_license(
        tenant_id=tenant.id, order_item_id=item.id, product_id=product.id
    )
    assert licence.key.startswith("LIC-") and len(licence.key) == 20
    assert licence.status == "active"
    assert LicenseKey.query.filter_by(id=licence.id).one().order_item_id == item.id


# ---------------------------------------------------------------------------
# fraud_svc.fraud_service
# ---------------------------------------------------------------------------


def _fraud_rule(
    tenant_id: int, rule_type: str, operator: str, threshold: str, name: str
):
    return FraudService().create_rule(
        tenant_id=tenant_id,
        name=name,
        rule_type=rule_type,
        operator=operator,
        threshold_value=threshold,
    )


@pytest.mark.parametrize(
    ("operator", "threshold", "should_match"),
    [
        (">=", "100", True),
        ("gte", "100", True),
        ("<", "200", True),
        ("lt", "200", True),
        ("<=", "100", True),
        ("lte", "100", True),
        ("==", "100", True),
        ("eq", "100", True),
        ("!=", "5", True),
        ("neq", "5", True),
        ("LIKE", "100", False),
    ],
)
def test_fraud_compare_operators(app, tenant, operator, threshold, should_match):
    rule = _fraud_rule(
        tenant.id, "amount", operator, threshold, f"op-{operator}-{_token()}"
    )
    order = _order(tenant.id, total="100")
    result = FraudService().evaluate_order(
        tenant_id=tenant.id, order_id=order.id, context={}
    )
    assert result["matched_rules"] == ([rule.name] if should_match else [])
    assert result["decision"] == ("review" if should_match else "approve")
    assert FraudReview.query.filter_by(order_id=order.id).count() == (
        1 if should_match else 0
    )


def test_fraud_first_order_guest_and_custom_metrics(app, db_session, tenant):
    svc = FraudService()
    first = _fraud_rule(tenant.id, "first_order", "eq", "1", "first-order")
    order = _order(tenant.id, email="first@test.com", is_guest=False)
    assert (
        svc.evaluate_order(
            tenant_id=tenant.id, order_id=order.id, context={"is_first_order": False}
        )["decision"]
        == "approve"
    )
    result = svc.evaluate_order(
        tenant_id=tenant.id, order_id=order.id, context={"is_first_order": True}
    )
    assert result["matched_rules"] == [first.name]
    assert result["risk_score"] == 30

    # Without an explicit context flag the rule counts the customer's orders.
    db_order = _order(tenant.id, email="counted@test.com", is_guest=False)
    counted = svc.evaluate_order(tenant_id=tenant.id, order_id=db_order.id)
    assert counted["matched_rules"] == [first.name]
    second_order = _order(tenant.id, email="counted@test.com", is_guest=False)
    assert (
        svc.evaluate_order(tenant_id=tenant.id, order_id=second_order.id)[
            "matched_rules"
        ]
        == []
    )

    guest = _fraud_rule(tenant.id, "guest_order", "eq", "1", "guest")
    guest_order = _order(tenant.id, is_guest=True)
    guest_result = svc.evaluate_order(
        tenant_id=tenant.id,
        order_id=guest_order.id,
        context={"is_first_order": False},
    )
    assert guest_result["matched_rules"] == [guest.name]
    assert guest_result["risk_score"] == 15
    registered = _order(tenant.id, is_guest=False)
    assert (
        svc.evaluate_order(
            tenant_id=tenant.id,
            order_id=registered.id,
            context={"is_first_order": False},
        )["decision"]
        == "approve"
    )

    custom = _fraud_rule(tenant.id, "custom_metric", "gt", "3", "custom")
    custom_order = _order(tenant.id, is_guest=False)
    context = {"custom_metric": "5", "is_first_order": False}
    assert svc.evaluate_order(
        tenant_id=tenant.id, order_id=custom_order.id, context=context
    )["matched_rules"] == [custom.name]
    # A non-numeric custom metric is treated as 0 (no match, no false alarm).
    bad_value = _order(tenant.id, is_guest=False)
    bad_result = svc.evaluate_order(
        tenant_id=tenant.id,
        order_id=bad_value.id,
        context={"custom_metric": "not-a-number", "is_first_order": False},
    )
    assert bad_result["matched_rules"] == []
    assert FraudReview.query.filter_by(order_id=bad_value.id).count() == 0
    absent = _order(tenant.id, is_guest=False)
    assert (
        svc.evaluate_order(
            tenant_id=tenant.id,
            order_id=absent.id,
            context={"is_first_order": False},
        )["decision"]
        == "approve"
    )


def test_fraud_rule_listing_score_clamp_reviewer_and_chargeback(
    app, db_session, tenant
):
    svc = FraudService()
    for idx in range(4):
        _fraud_rule(tenant.id, "amount", "gt", "1", f"high-{idx}")
    inactive = _fraud_rule(tenant.id, "amount", "gt", "1", "inactive")
    inactive.is_active = False
    db_session.commit()
    # list_rules returns every tenant rule (active and inactive alike).
    assert {rule.id for rule in svc.list_rules(tenant.id)} == {
        rule.id for rule in FraudRule.query.filter_by(tenant_id=tenant.id)
    }
    assert len(svc.list_rules(tenant.id)) == 5
    assert svc.list_rules(tenant.id + 1000) == []

    reviewer = _user(tenant.id)
    order = _order(tenant.id, total="100")
    result = svc.evaluate_order(
        tenant_id=tenant.id,
        order_id=order.id,
        context={"reviewed_by": reviewer.id},
    )
    assert len(result["matched_rules"]) == 4
    assert "inactive" not in result["matched_rules"]
    assert result["risk_score"] == 100
    assert result["created"] is True
    review = FraudReview.query.filter_by(order_id=order.id).one()
    assert review.reviewed_by == reviewer.id
    assert "high-0" in (review.notes or "")

    payment, _event = _payment(tenant.id, order.id)
    chargeback = svc.chargeback(
        tenant_id=tenant.id,
        payment_id=payment.id,
        order_id=order.id,
        amount="75.50",
        reason_code="fraudulent",
    )
    assert chargeback.amount == Decimal("75.50")
    assert chargeback.status == "disputed"
    assert chargeback.reason_code == "fraudulent"
    assert Chargeback.query.filter_by(id=chargeback.id).one().payment_id == payment.id


def test_fraud_subscriber_ignores_incomplete_and_bad_payloads(app, db_session, tenant):
    # No tenant/order id: nothing to evaluate.
    on_order_created()
    on_order_created(tenant_id=tenant.id)
    # A malformed id raises inside the subscriber but must never propagate or
    # leave the session in a broken state (checkout must not be blocked).
    on_order_created(tenant_id="not-an-int", order_id=1)
    assert FraudRule.query.filter_by(tenant_id=tenant.id).count() == 0
    assert FraudReview.query.count() == 0


# ---------------------------------------------------------------------------
# feature_flag_svc.feature_flag_service
# ---------------------------------------------------------------------------


def test_feature_flag_lookup_rollout_overrides_and_removal(app, db_session, tenant):
    svc = FeatureFlagService()
    svc.ensure_seeded()
    svc.ensure_seeded()  # idempotent
    assert FeatureFlag.query.filter_by(code="draft_orders_enabled").count() == 1

    with pytest.raises(NotFoundError):
        svc.get_by_code("does_not_exist")

    # rollout_percent >= 100 falls back to the flag default; <= 0 disables it.
    assert svc.is_enabled(tenant_id=tenant.id, code="draft_orders_enabled") is True
    assert svc.is_enabled(tenant_id=tenant.id, code="ai_enabled") is False
    zero = FeatureFlag(
        name="Never",
        code="never_enabled",
        category="test",
        default_value=True,
        scope="tenant",
        is_system=False,
        rollout_percent=0,
    )
    db_session.add(zero)
    db_session.commit()
    assert svc.is_enabled(tenant_id=tenant.id, code="never_enabled") is False

    reviewer = _user(tenant.id)
    # The service reads ``user.name`` for the audit display name, while the
    # User model only defines first_name/last_name. Provide a transient display
    # name so that the naming branch can still be exercised against a real row.
    reviewer.name = "Reviewer"
    override = svc.set_tenant_override(
        tenant_id=tenant.id,
        code="ai_enabled",
        value=True,
        reason="pilot",
        set_by=reviewer.id,
    )
    assert override["value"] is True and override["has_override"] is True
    assert svc.is_enabled(tenant_id=tenant.id, code="ai_enabled") is True
    listed = {flag["code"]: flag for flag in svc.list_for_tenant(tenant.id)}
    assert listed["ai_enabled"]["has_override"] is True
    assert listed["ai_enabled"]["override_reason"] == "pilot"
    assert listed["ai_enabled"]["override_set_by"] == reviewer.id
    assert listed["ai_enabled"]["override_set_by_name"] == "Reviewer"
    assert listed["draft_orders_enabled"]["has_override"] is False
    assert TenantFeatureFlagOverride.query.filter_by(tenant_id=tenant.id).count() == 1

    updated = svc.set_tenant_override(
        tenant_id=tenant.id,
        code="ai_enabled",
        value=False,
        reason="rolled back",
        set_by=None,
    )
    assert updated["value"] is False
    assert svc.is_enabled(tenant_id=tenant.id, code="ai_enabled") is False
    assert {flag["code"]: flag for flag in svc.list_for_tenant(tenant.id)}[
        "ai_enabled"
    ]["override_set_by_name"] is None

    svc.remove_tenant_override(tenant_id=tenant.id, code="ai_enabled")
    assert TenantFeatureFlagOverride.query.filter_by(tenant_id=tenant.id).count() == 0
    assert svc.is_enabled(tenant_id=tenant.id, code="ai_enabled") is False
    # Removing an absent override is a no-op.
    svc.remove_tenant_override(tenant_id=tenant.id, code="ai_enabled")


# ---------------------------------------------------------------------------
# platform_svc.commission_service
# ---------------------------------------------------------------------------


def test_commission_apply_guards_and_missing_original(app, db_session, tenant):
    svc = CommissionService()
    order = _order(tenant.id)
    no_commission = FinancialEventsService().record_inbound(
        tenant_id=tenant.id,
        amount="100.00",
        event_type="order.payment",
        source_entity="order",
        source_id=order.id,
        apply_commission=False,
    )
    assert svc.apply_from_event(no_commission, order_id=order.id) is None
    assert svc.reverse(no_commission) is None

    payment, event = _payment(tenant.id, order.id)
    ledger = svc.apply_from_event(event, payment_id=payment.id, order_id=order.id)
    assert ledger is not None
    again = svc.apply_from_event(event, payment_id=payment.id, order_id=order.id)
    assert again.id == ledger.id
    assert event.commission_ledger_id == ledger.id
    assert svc._create_reversal(original=None, event=event) is None


def test_commission_reverse_metadata_partial_and_missing_entities(
    app, db_session, tenant
):
    svc = CommissionService()
    order = _order(tenant.id)
    payment, event = _payment(tenant.id, order.id)
    original = svc.apply_from_event(event, payment_id=payment.id, order_id=order.id)

    assert svc.reverse_for_payment(tenant.id, 999_999) is None
    assert svc.reverse_for_payment(tenant.id, payment.id) is None  # no refund yet

    refund, outbound = _refund_with_event(
        tenant.id,
        payment,
        amount="100.00",
        metadata={"reverses_financial_event_id": event.id},
    )
    reversal = svc.reverse(outbound)
    assert reversal is not None
    assert reversal.reverses_ledger_id == original.id
    assert reversal.direction == "debit"
    assert reversal.gross_amount == Decimal("-100.00")
    assert svc.reverse(outbound).id == reversal.id  # idempotent
    assert len(_reversals(tenant.id)) == 1

    # A refund event without metadata is resolved via its refund row.
    standalone = FinancialEvent(
        tenant_id=tenant.id,
        direction="outbound",
        event_type="payment.refund",
        amount=Decimal("-100.00"),
        currency="ILS",
        source_entity="refund",
        source_id=refund.id,
        commission_applied=False,
        status="completed",
    )
    db_session.add(standalone)
    db_session.commit()
    assert svc.reverse(standalone).id == reversal.id

    # Partial refunds are keyed by their own financial event and coexist with
    # the full reversal. A fresh payment keeps the refund lookup unambiguous.
    partial_order = _order(tenant.id)
    partial_payment, partial_inbound = _payment(tenant.id, partial_order.id)
    partial_original = svc.apply_from_event(
        partial_inbound, payment_id=partial_payment.id, order_id=partial_order.id
    )
    _partial_refund, partial_event = _refund_with_event(
        tenant.id, partial_payment, amount="40.00", metadata=None
    )
    partial = svc.reverse_for_payment(tenant.id, partial_payment.id)
    assert partial is not None
    assert partial.financial_event_id == partial_event.id
    assert partial.reverses_ledger_id == partial_original.id
    assert partial.gross_amount == Decimal("-40.00")
    expected_commission = -(
        abs(partial_original.commission_amount) * Decimal("0.4")
    ).quantize(Decimal("0.01"))
    assert partial.commission_amount == expected_commission
    assert len(_reversals(tenant.id)) == 2

    # An over-refund is capped at 100% of the original commission.
    over_order = _order(tenant.id)
    over_payment, over_inbound = _payment(tenant.id, over_order.id)
    over_original = svc.apply_from_event(
        over_inbound, payment_id=over_payment.id, order_id=over_order.id
    )
    _over_refund, over_event = _refund_with_event(
        tenant.id, over_payment, amount="150.00", metadata=None
    )
    capped = svc.reverse_for_payment(tenant.id, over_payment.id)
    assert capped.financial_event_id == over_event.id
    assert capped.reverses_ledger_id == over_original.id
    assert capped.gross_amount == Decimal("-100.00")
    assert capped.commission_amount == -abs(over_original.commission_amount)
    assert len(_reversals(tenant.id)) == 3

    # A refund whose financial event belongs to another tenant cannot be used.
    other_tenant = TenantService().create_tenant(
        name="Other",
        slug=f"other-{_token()}",
        email=f"other-{_token()}@test.com",
    )
    foreign_order = _order(other_tenant.id)
    foreign_event = FinancialEventsService().record_inbound(
        tenant_id=other_tenant.id,
        amount="10.00",
        event_type="order.payment",
        source_entity="order",
        source_id=foreign_order.id,
        apply_commission=False,
    )
    isolated_payment, _ = _payment(tenant.id, order.id, with_event=False)
    orphan_refund = Refund(
        tenant_id=tenant.id,
        payment_id=isolated_payment.id,
        amount=Decimal("10.00"),
        currency="ILS",
        status="completed",
        financial_event_id=foreign_event.id,
    )
    db_session.add(orphan_refund)
    db_session.commit()
    assert svc.reverse_for_payment(tenant.id, isolated_payment.id) is None


# ---------------------------------------------------------------------------
# payment_svc.external_refund_service
# ---------------------------------------------------------------------------


def test_external_refund_records_ledger_event_and_reversal(app, db_session, tenant):
    order = _order(tenant.id)
    payment, event = _payment(tenant.id, order.id)
    original = CommissionService().apply_from_event(
        event, payment_id=payment.id, order_id=order.id
    )

    result = record_external_refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
        amount="40.00",
        provider_refund_id=f"prov-{_token()}",
        reason="customer changed mind",
    )
    refund = Refund.query.filter_by(payment_id=payment.id).one()
    assert result["refund"]["id"] == refund.id
    assert result["refund"]["amount"] == "40.00"
    assert result["uncertain"] is False
    assert refund.status == "completed" and refund.reason == "customer changed mind"
    outbound = FinancialEvent.query.filter_by(id=refund.financial_event_id).one()
    assert outbound.amount == Decimal("-40.00")
    assert outbound.event_type == "payment.refund"
    assert outbound.metadata_json == {"reverses_financial_event_id": event.id}
    assert Payment.query.filter_by(id=payment.id).one().status == "completed"

    reversals = _reversals(tenant.id)
    assert len(reversals) == 1
    assert reversals[0].reverses_ledger_id == original.id
    assert reversals[0].gross_amount == Decimal("-40.00")


def test_external_refund_full_amount_closes_payment(app, db_session, tenant):
    order = _order(tenant.id)
    payment, _event = _payment(tenant.id, order.id)
    result = record_external_refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
        provider_refund_id=None,
    )
    assert result["refund"]["amount"] == str(payment.amount)
    assert result["provider_refund_id"] is None
    assert Payment.query.filter_by(id=payment.id).one().status == "refunded"


def test_external_refund_validates_all_bad_inputs(app, db_session, tenant):
    order = _order(tenant.id)
    payment, _event = _payment(tenant.id, order.id)

    with pytest.raises(NotFoundError):
        record_external_refund(tenant_id=tenant.id, payment_public_id="not-a-uuid")
    with pytest.raises(NotFoundError):
        record_external_refund(tenant_id=tenant.id, payment_public_id=str(uuid.uuid4()))

    pending_order = _order(tenant.id)
    pending, _ = _payment(tenant.id, pending_order.id, status="pending")
    with pytest.raises(ValidationError, match="completed payments"):
        record_external_refund(
            tenant_id=tenant.id, payment_public_id=str(pending.public_id)
        )

    for bad_amount in ("abc", "0", "-1", "1000.00"):
        with pytest.raises(ValidationError):
            record_external_refund(
                tenant_id=tenant.id,
                payment_public_id=str(payment.public_id),
                amount=bad_amount,
            )
    assert Refund.query.filter_by(payment_id=payment.id).count() == 0

    record_external_refund(
        tenant_id=tenant.id,
        payment_public_id=str(payment.public_id),
        amount="25.00",
        provider_refund_id="provider-refund-1",
    )
    with pytest.raises(ConflictError, match="already recorded"):
        record_external_refund(
            tenant_id=tenant.id,
            payment_public_id=str(payment.public_id),
            amount="25.00",
            provider_refund_id="provider-refund-1",
        )
    assert Refund.query.filter_by(payment_id=payment.id).count() == 1
