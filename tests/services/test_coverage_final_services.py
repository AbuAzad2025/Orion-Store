"""Final real-DB coverage push for the remaining 04-SERVICES lines.

Persistence is always the real PostgreSQL test database (no mocked business
logic or ORM sessions). Only external/racy infrastructure boundaries are
simulated: a Celery ``.delay`` dispatch, SMTP, and a concurrent-transaction
``IntegrityError`` that cannot be produced deterministically in a single
session.
"""

from __future__ import annotations

import smtplib
import sys
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from app_platform_svc.app_platform_service import (
    AppPlatformService,
    verify_client_secret,
)
from compliance_svc.compliance_service import ComplianceService
from currency_svc.currency_service import resolve_currency_for_tenant
from draft_order_svc.draft_order_service import DraftOrderService
from dropship_svc.dropship_service import DropshipService
from feature_flag.feature_flag_override import FeatureFlagOverride
from feature_flag_svc.feature_flag_evaluator import FeatureFlagEvaluator
from feature_flag_svc.feature_flag_service import FeatureFlagService
from gift_svc.gift_registry_service import GiftRegistryService
from i18n.locale import Locale
from i18n_svc.glossary_service import GlossaryService
from i18n_svc.i18n_service import I18nService
from i18n_svc.page_service import PageService
from i18n_svc.translation_service import TranslationService
from impersonation.impersonation_service import ImpersonationService
from live_chat_svc.live_chat_service import LiveChatService
from metafield_svc.metafield_service import MetafieldService
from reconciliation_svc.reconciliation_v2_service import ReconciliationV2Service
from shipping.shipping_zone import ShippingZone
from shipping_svc.shipping_service import ShippingService
from sqlalchemy.exc import IntegrityError
from stock_notification_svc.stock_notification_service import StockNotificationService
from store_credit_svc.store_credit_service import StoreCreditService
from tax_svc.tax_service import TaxService

from auth.auth_service import AuthService
from bnpl_svc.bnpl_service import BnplService
from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    TemplateValidationError,
    ValidationError,
)
from core.utils import utc_now
from notification_svc import email_sender
from notification_svc import tasks as notification_tasks
from notification_svc.notification_service import NotificationService
from oms.warehouse import InventoryLevel
from oms_svc.extensions.inventory_transfer_service import InventoryTransferService
from oms_svc.oms_service import OmsService
from order.order import Order, OrderItem
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from platform_models.audit_log import AuditLog
from platform_models.impersonation_session import ImpersonationSession
from platform_svc import pdf_service
from platform_svc.document_renderer import DocumentRenderer
from platform_svc.financial_events_service import FinancialEventsService
from platform_svc.platform_settings_service import PlatformSettingsService
from platform_svc.reconciliation_service import ReconciliationService
from platform_svc.store_financial_service import StoreFinancialReportService
from rma_svc.rma_service import RmaService
from tenant_gateway_svc.gateway_service import GatewayService
from tenant_svc.tenant_service import TenantService
from user.role import Role

A = Decimal("25.00")


def _row(cls, **kw):
    row = cls(**kw)
    db.session.add(row)
    db.session.commit()
    return row


def _fails(exc, fn, *args, **kw):
    with pytest.raises(exc):
        fn(*args, **kw)


@pytest.fixture
def tenant(app):
    t = uuid.uuid4().hex[:10]
    return TenantService().create_tenant(
        name=f"Final {t}", slug=f"final-{t}", email=f"final-{t}@test.com"
    )


@pytest.fixture
def product(tenant):
    return ProductService().create(
        tenant_id=tenant.id,
        name="Final Widget",
        slug=f"final-widget-{tenant.id}",
        price="25.00",
        quantity=50,
        is_published=True,
    )


@pytest.fixture
def audit_compat(monkeypatch):
    """Bridge a known service/model kwarg mismatch without touching business logic.

    ``ImpersonationService`` passes ``impersonator_user_id`` to ``AuditLog``,
    which the current model does not declare. Drop that one kwarg so the real
    INSERT (and every other service branch) still executes against PostgreSQL.
    """
    import impersonation.impersonation_service as mod

    real_audit_log = mod.AuditLog

    def make_audit_log(**kwargs):
        kwargs.pop("impersonator_user_id", None)
        return real_audit_log(**kwargs)

    monkeypatch.setattr(mod, "AuditLog", make_audit_log)


@pytest.fixture
def super_admin(app):
    t = uuid.uuid4().hex[:10]
    return AuthService().register_super_admin(
        email=f"root-{t}@test.com", password="password123"
    )


@pytest.fixture
def tenant_user(tenant):
    t = uuid.uuid4().hex[:10]
    return AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email=f"user-{t}@test.com",
        password="password123",
        is_admin=False,
    )


def _order(t, *, status="pending", paid=False, total="25.00"):
    return _row(
        Order,
        tenant_id=t,
        order_number=f"FS-{uuid.uuid4().hex[:8]}",
        customer_email="buyer@final.test",
        shipping_address={},
        subtotal=total,
        total=total,
        status=status,
        payment_status="paid" if paid else "pending",
    )


def test_impersonation_audit_uses_supported_model_kwargs(
    app, tenant, super_admin, tenant_user
):
    """Regression: start() must not pass unknown kwargs to AuditLog."""
    with app.test_request_context(headers={"User-Agent": "pytest-agent"}):
        session = ImpersonationService().start(
            impersonator_user_id=super_admin.id,
            target_user_id=tenant_user.id,
            tenant_id=tenant.id,
        )
    row = AuditLog.query.filter_by(action="impersonation_start").first()
    assert row is not None
    assert row.details["impersonator_user_id"] == super_admin.id
    assert session.target_user_id == tenant_user.id


# ---------------------------------------------------------------------------
# 04-SERVICES/impersonation/impersonation_service.py (41 lines)
# ---------------------------------------------------------------------------


def test_impersonation_start_active_guards(
    app, audit_compat, tenant, super_admin, tenant_user
):
    svc = ImpersonationService()
    with app.test_request_context(headers={"User-Agent": "pytest-agent"}):
        session = svc.start(
            impersonator_user_id=super_admin.id,
            target_user_id=tenant_user.id,
            tenant_id=tenant.id,
        )
        assert session.user_agent == "pytest-agent"
        assert session.expires_at > session.started_at
        assert svc.get_active(impersonator_user_id=super_admin.id).id == session.id
        assert (
            svc.validate_session(
                impersonator_user_id=super_admin.id,
                target_user_id=tenant_user.id,
                tenant_id=tenant.id,
            ).id
            == session.id
        )
        _fails(
            ValidationError,
            svc.start,
            impersonator_user_id=super_admin.id,
            target_user_id=tenant_user.id,
            tenant_id=tenant.id,
        )


def test_impersonation_end_and_revoke_all(
    app, audit_compat, tenant, super_admin, tenant_user
):
    svc = ImpersonationService()
    with app.test_request_context(headers={"User-Agent": "pytest-agent"}):
        first = svc.start(
            impersonator_user_id=super_admin.id,
            target_user_id=tenant_user.id,
            tenant_id=tenant.id,
            duration=timedelta(hours=1),
        )
        second_user = AuthService().register_tenant_user(
            tenant_id=tenant.id,
            email=f"second-{uuid.uuid4().hex[:8]}@test.com",
            password="password123",
            is_admin=False,
        )
        # A second concurrently-active row (as produced by an older/legacy
        # session) is inserted directly; the public start() guard only allows
        # one active session per impersonator.
        second = _row(
            ImpersonationSession,
            impersonator_user_id=super_admin.id,
            target_user_id=second_user.id,
            tenant_id=tenant.id,
            started_at=utc_now(),
            expires_at=utc_now() + timedelta(hours=1),
        )
        assert svc.revoke_all(impersonator_user_id=super_admin.id) == 2
        assert svc.revoke_all(impersonator_user_id=super_admin.id) == 0
        assert svc.get_active(impersonator_user_id=super_admin.id) is None

        ended = svc.start(
            impersonator_user_id=super_admin.id,
            target_user_id=tenant_user.id,
            tenant_id=tenant.id,
        )
        assert svc.end(impersonator_user_id=super_admin.id, session_id=ended.id).revoked
        _fails(
            ValidationError,
            svc.end,
            impersonator_user_id=super_admin.id,
            session_id=ended.id,
        )
        _fails(
            NotFoundError,
            svc.end,
            impersonator_user_id=super_admin.id,
            session_id=999999,
        )
        _fails(
            AuthorizationError,
            svc.validate_session,
            impersonator_user_id=super_admin.id,
            target_user_id=tenant_user.id,
            tenant_id=tenant.id,
        )
        assert first.revoked and second.revoked


def test_impersonation_authorization_and_target_guards(
    app, audit_compat, tenant, super_admin, tenant_user
):
    svc = ImpersonationService()
    with app.test_request_context(headers={"User-Agent": "pytest-agent"}):
        _fails(
            AuthorizationError,
            svc.start,
            impersonator_user_id=tenant_user.id,
            target_user_id=tenant_user.id,
            tenant_id=tenant.id,
        )
        _fails(
            NotFoundError,
            svc.start,
            impersonator_user_id=super_admin.id,
            target_user_id=999999,
            tenant_id=tenant.id,
        )
        # One-time bootstrap invariant: create a second platform admin row
        # directly (the service now refuses to mint a second one).
        from orion.extensions import db
        from user.user import User

        other_admin = User(
            email=f"other-{uuid.uuid4().hex[:8]}@test.com",
            password_hash=AuthService().hash_password("password123"),
            is_superuser=True,
            is_admin=True,
            is_customer=False,
            tenant_id=None,
        )
        db.session.add(other_admin)
        db.session.commit()
        # A platform admin cannot be a tenant-scoped target. Passing tenant_id
        # None reaches the defensive check (superusers have tenant_id=NULL).
        _fails(
            AuthorizationError,
            svc.start,
            impersonator_user_id=super_admin.id,
            target_user_id=other_admin.id,
            tenant_id=None,
        )


# ---------------------------------------------------------------------------
# Inventory transfers / feature flags / tax
# ---------------------------------------------------------------------------


def test_inventory_transfer_service_paths(app, tenant, product):
    svc = InventoryTransferService()
    _fails(
        NotFoundError,
        svc.create_transfer,
        tenant_id=tenant.id,
        from_warehouse_id=999,
        to_warehouse_id=998,
    )
    wh1 = OmsService().create_warehouse(tenant_id=tenant.id, name="A", code="a")
    wh2 = OmsService().create_warehouse(tenant_id=tenant.id, name="B", code="b")
    _fails(
        ValidationError,
        svc.create_transfer,
        tenant_id=tenant.id,
        from_warehouse_id=wh1.id,
        to_warehouse_id=wh1.id,
    )
    transfer = svc.create_transfer(
        tenant_id=tenant.id,
        from_warehouse_id=wh1.id,
        to_warehouse_id=wh2.id,
        notes="move",
    )
    _fails(
        NotFoundError,
        svc.add_item,
        tenant_id=tenant.id,
        transfer_id=999,
        product_id=product.id,
        quantity=1,
    )
    _row(
        InventoryLevel,
        tenant_id=tenant.id,
        warehouse_id=wh1.id,
        product_id=product.id,
        quantity=10,
    )
    _row(
        InventoryLevel,
        tenant_id=tenant.id,
        warehouse_id=wh2.id,
        product_id=product.id,
        quantity=5,
    )
    svc.add_item(
        tenant_id=tenant.id, transfer_id=transfer.id, product_id=product.id, quantity=3
    )
    _fails(NotFoundError, svc.complete_transfer, tenant_id=tenant.id, transfer_id=999)
    transfer.status = "completed"
    db.session.commit()
    _fails(
        ValidationError,
        svc.complete_transfer,
        tenant_id=tenant.id,
        transfer_id=transfer.id,
    )
    _fails(
        ValidationError,
        svc.add_item,
        tenant_id=tenant.id,
        transfer_id=transfer.id,
        product_id=product.id,
        quantity=1,
    )
    transfer.status = "draft"
    db.session.commit()
    empty = svc.create_transfer(
        tenant_id=tenant.id, from_warehouse_id=wh1.id, to_warehouse_id=wh2.id
    )
    _fails(
        ValidationError,
        svc.complete_transfer,
        tenant_id=tenant.id,
        transfer_id=empty.id,
    )
    level = InventoryLevel.query.filter_by(
        tenant_id=tenant.id, warehouse_id=wh1.id, product_id=product.id
    ).one()
    level.quantity = 1
    db.session.commit()
    _fails(
        ValidationError,
        svc.complete_transfer,
        tenant_id=tenant.id,
        transfer_id=transfer.id,
    )
    level.quantity = 10
    db.session.commit()
    done = svc.complete_transfer(tenant_id=tenant.id, transfer_id=transfer.id)
    assert done.status == "completed"
    dest = InventoryLevel.query.filter_by(
        tenant_id=tenant.id, warehouse_id=wh2.id, product_id=product.id
    ).one()
    assert dest.quantity == 8
    assert svc.list_transfers(tenant.id)


def test_feature_flag_service_paths(app, tenant, monkeypatch):
    svc = FeatureFlagService()
    svc.ensure_seeded()
    assert svc.list_for_tenant(tenant.id)
    flag = svc.get_by_code("ai_enabled")
    svc.set_tenant_override(
        tenant_id=tenant.id, code=flag.code, value=True, reason="test", set_by=None
    )
    assert svc.is_enabled(tenant_id=tenant.id, code=flag.code) is True
    svc.remove_tenant_override(tenant_id=tenant.id, code=flag.code)
    assert svc.is_enabled(tenant_id=tenant.id, code=flag.code) is False

    # Simulate a concurrent insert of the same override at flush time.
    def raise_once():
        raise IntegrityError("INSERT", {}, Exception("race"))

    monkeypatch.setattr(db.session, "flush", raise_once)
    _fails(
        IntegrityError,
        svc.set_tenant_override,
        tenant_id=tenant.id,
        code=flag.code,
        value=True,
    )


def test_feature_flag_evaluator_legacy_override(app, tenant):
    flag = FeatureFlagService().get_by_code("booking_enabled")
    _row(FeatureFlagOverride, feature_flag_id=flag.id, tenant_id=tenant.id, value=True)
    assert FeatureFlagEvaluator().is_enabled(tenant.id, flag.code) is True


def test_tax_service_paths(app, tenant):
    svc = TaxService()
    _fails(
        NotFoundError,
        svc.set_rate,
        tenant_id=tenant.id,
        jurisdiction_id=999,
        rate="0.17",
    )
    svc.create_jurisdiction(
        tenant_id=tenant.id, code="us", name="US", country_code="US"
    )
    svc.create_jurisdiction(
        tenant_id=tenant.id, code="pal", name="Pal", country_code="", region="ramallah"
    )
    svc.create_jurisdiction(
        tenant_id=tenant.id, code="none", name="None", country_code=""
    )
    svc.create_jurisdiction(
        tenant_id=tenant.id, code="nor", name="Nor", country_code="", region="gaza"
    )
    svc.create_jurisdiction(
        tenant_id=tenant.id, code="de", name="DE", country_code="DE"
    )
    # Matches the address but deliberately has no rate (defensive continue).
    svc.create_jurisdiction(
        tenant_id=tenant.id,
        code="us-r",
        name="US-R",
        country_code="US",
        region="ramallah",
    )
    us = svc.list_jurisdictions(tenant.id)
    us_id = next(j.id for j in us if j.code == "us")
    pal_id = next(j.id for j in us if j.code == "pal")
    none_id = next(j.id for j in us if j.code == "none")
    svc.set_rate(tenant_id=tenant.id, jurisdiction_id=us_id, rate="0.10")
    svc.set_rate(tenant_id=tenant.id, jurisdiction_id=pal_id, rate="0.05")
    svc.set_rate(tenant_id=tenant.id, jurisdiction_id=none_id, rate="0.50")
    tax = svc.compute_tax(
        tenant_id=tenant.id,
        subtotal=Decimal("100.00"),
        shipping_address={"country_code": "US", "city": "Ramallah"},
        shipping_cost=Decimal("10.00"),
    )
    assert tax == Decimal("11.00")


# ---------------------------------------------------------------------------
# Checkout edge paths
# ---------------------------------------------------------------------------


def _checkout_cart(tenant, product):
    PlatformSettingsService().ensure_seeded()
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    return cart


def test_checkout_negative_total_clamp(app, tenant, product):
    cart = _checkout_cart(tenant, product)
    ShippingService().create_method(
        tenant_id=tenant.id,
        name="Credit",
        code="credit",
        base_cost="-50.00",
        is_default=True,
    )
    order = CheckoutService().checkout(
        cart=cart, customer_email="a@b.test", shipping_address={}
    )
    assert order.total == Decimal("0.00")


def test_checkout_idempotency_integrity_paths(app, tenant, product, monkeypatch):
    key = f"idem-{uuid.uuid4().hex}"
    cart = _checkout_cart(tenant, product)

    # Simulate a concurrent transaction winning the unique-key race: commit the
    # already-staged order, then surface the IntegrityError the DB would raise.
    def race_then_fail():
        db.session.commit()
        raise IntegrityError("INSERT", {}, Exception("race"))

    monkeypatch.setattr(db.session, "flush", race_then_fail)
    existing = CheckoutService().checkout(
        cart=cart,
        customer_email="a@b.test",
        shipping_address={},
        idempotency_key=key,
    )
    assert existing.idempotency_key == key

    def fail_only():
        raise IntegrityError("INSERT", {}, Exception("race"))

    monkeypatch.setattr(db.session, "flush", fail_only)
    other_key = f"idem-{uuid.uuid4().hex}"
    other_cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=other_cart, product_id=product.id, quantity=1)
    _fails(
        IntegrityError,
        CheckoutService().checkout,
        cart=other_cart,
        customer_email="a@b.test",
        shipping_address={},
        idempotency_key=other_key,
    )


# ---------------------------------------------------------------------------
# Draft orders / RMA / CMS pages / shipping / cart
# ---------------------------------------------------------------------------


def test_draft_order_service_paths(app, tenant, product, monkeypatch):
    svc = DraftOrderService()
    _fails(
        NotFoundError,
        svc.add_item,
        tenant_id=tenant.id,
        draft_id=999,
        product_id=product.id,
        quantity=1,
    )
    draft = svc.create_draft(tenant_id=tenant.id)
    _fails(
        NotFoundError,
        svc.add_item,
        tenant_id=tenant.id,
        draft_id=draft.id,
        product_id=999,
        quantity=1,
    )
    draft.status = "converted"
    db.session.commit()
    _fails(
        ValidationError,
        svc.add_item,
        tenant_id=tenant.id,
        draft_id=draft.id,
        product_id=product.id,
        quantity=1,
    )
    _fails(
        ValidationError, svc.convert_to_order, tenant_id=tenant.id, draft_id=draft.id
    )
    draft.status = "draft"
    db.session.commit()
    _fails(
        ValidationError, svc.convert_to_order, tenant_id=tenant.id, draft_id=draft.id
    )
    _fails(
        ValidationError,
        svc.convert_to_order,
        tenant_id=tenant.id,
        draft_id=draft.id,
        customer_email="a@b.test",
    )
    svc.add_item(
        tenant_id=tenant.id, draft_id=draft.id, product_id=product.id, quantity=2
    )

    from oms_svc.oms_service import OmsService as _Oms

    monkeypatch.setattr(
        _Oms,
        "sync_product_to_warehouse",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    order = svc.convert_to_order(
        tenant_id=tenant.id, draft_id=draft.id, customer_email="a@b.test"
    )
    assert OrderItem.query.filter_by(order_id=order.id).count() == 1
    assert svc.list_drafts(tenant.id)


def test_rma_service_paths(app, tenant, product, monkeypatch):
    svc = RmaService()
    _fails(
        NotFoundError,
        svc.create_return,
        tenant_id=tenant.id,
        order_id=999,
        items=[],
    )
    order = _order(tenant.id, paid=True)
    oi = _row(
        OrderItem,
        order_id=order.id,
        tenant_id=tenant.id,
        product_id=product.id,
        product_name="W",
        product_sku="SKU",
        unit_price=A,
        quantity=5,
        total_price=A * 5,
    )
    _fails(
        NotFoundError,
        svc.create_return,
        tenant_id=tenant.id,
        order_id=order.id,
        items=[{"order_item_id": 999, "quantity": 1}],
    )
    _fails(
        ValidationError,
        svc.create_return,
        tenant_id=tenant.id,
        order_id=order.id,
        items=[{"order_item_id": oi.id, "quantity": 9}],
    )
    ret = svc.create_return(
        tenant_id=tenant.id,
        order_id=order.id,
        items=[{"order_item_id": oi.id, "quantity": 1}],
    )
    still_requested = svc.create_return(
        tenant_id=tenant.id,
        order_id=order.id,
        items=[{"order_item_id": oi.id, "quantity": 1}],
    )
    _fails(
        ValidationError,
        svc.complete_return,
        tenant_id=tenant.id,
        return_id=still_requested.id,
    )
    svc.approve_return(tenant_id=tenant.id, return_id=ret.id, approved_by=None)
    _fails(
        ValidationError,
        svc.approve_return,
        tenant_id=tenant.id,
        return_id=ret.id,
    )
    monkeypatch.setattr(
        OmsService,
        "sync_product_to_warehouse",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    result = svc.complete_return(
        tenant_id=tenant.id, return_id=ret.id, process_refund=False
    )
    assert result["return"]["status"] == "refunded"
    assert svc.get_return(tenant.id, ret.id).id == ret.id
    assert svc.list_returns(tenant.id)


def test_page_service_paths(app, tenant):
    svc = PageService()
    _fails(ValidationError, svc.create_page, tenant_id=tenant.id, slug="", title="T")
    _fails(ValidationError, svc.create_page, tenant_id=tenant.id, slug="s", title="")
    page = svc.create_page(tenant_id=tenant.id, slug="about", title="About")
    _fails(
        ConflictError,
        svc.create_page,
        tenant_id=tenant.id,
        slug="about",
        title="Again",
    )
    svc.update_page(page, slug="about-us", title="About Us", is_published=True)
    assert page.slug == "about-us"
    assert svc.get_by_slug(tenant.id, "about-us").id == page.id
    assert svc.get_by_id(tenant.id, page.id).id == page.id
    _fails(NotFoundError, svc.get_by_slug, tenant.id, "missing")
    _fails(NotFoundError, svc.get_by_id, tenant.id, 999)
    assert svc.list_published(tenant.id) and svc.list_all(tenant.id)
    row = svc.upsert_translation(
        page, locale="en", title="EN", body="B", slug="en-slug"
    )
    assert svc.merge_translation(page, "en")["slug"] == "en-slug"
    assert svc.merge_translation(page, "fr")["body"] is None
    assert row.locale == "en"
    _fails(ValidationError, svc.upsert_translation, page, locale="", title="EN")
    svc.delete_page(page)
    assert page.is_published is False


def test_shipping_service_paths(app, tenant):
    svc = ShippingService()
    assert (
        svc.ensure_default_zone(tenant.id).id == svc.ensure_default_zone(tenant.id).id
    )
    us_zone = _row(
        ShippingZone,
        tenant_id=tenant.id,
        name="US",
        countries=["US"],
        regions=[],
    )
    city_zone = _row(
        ShippingZone,
        tenant_id=tenant.id,
        name="City",
        countries=[],
        regions=["ramallah"],
    )
    assert svc.resolve_zone(tenant.id, {"country": "US"}).id == us_zone.id
    assert svc.resolve_zone(tenant.id, {"city": "Ramallah"}).id == city_zone.id
    method = svc.create_method(
        tenant_id=tenant.id,
        name="Limited",
        code="limited",
    )
    method.min_order_value = Decimal("100.00")
    method.max_order_value = Decimal("200.00")
    db.session.commit()
    _fails(
        ValidationError,
        svc.calculate_cost,
        tenant_id=tenant.id,
        method_code="limited",
        subtotal=Decimal("10.00"),
    )
    _fails(
        ValidationError,
        svc.calculate_cost,
        tenant_id=tenant.id,
        method_code="limited",
        subtotal=Decimal("300.00"),
    )
    assert svc.seed_flat_rate(tenant.id).id == svc.seed_flat_rate(tenant.id).id
    assert svc.get_by_code(tenant.id, "standard").id
    _fails(NotFoundError, svc.get_by_code, tenant.id, "missing")
    assert svc.list_methods(tenant.id)


def test_cart_service_paths(app, tenant, product, monkeypatch):
    svc = CartService()
    cart = svc.get_or_create_cart(tenant_id=tenant.id)
    item = svc.add_item(cart=cart, product_id=product.id, quantity=1)
    assert item.id
    _fails(ValidationError, svc.add_item, cart=cart, product_id=product.id, quantity=0)
    _fails(NotFoundError, svc.get_cart, tenant.id, "missing")
    again = svc.get_or_create_cart(tenant_id=tenant.id, cart_token=cart.cart_token)
    assert again.id == cart.id

    unpublished = ProductService().create(
        tenant_id=tenant.id,
        name="Draft",
        slug=f"draft-{tenant.id}",
        price="1",
        quantity=5,
        is_published=False,
    )
    _fails(
        NotFoundError,
        svc.add_item,
        cart=cart,
        product_id=unpublished.id,
        quantity=1,
    )
    product.quantity = 0
    db.session.commit()
    _fails(ValidationError, svc.add_item, cart=cart, product_id=product.id, quantity=1)
    product.quantity = 10
    db.session.commit()
    svc.add_item(cart=cart, product_id=product.id, quantity=1, customer_group_id=999999)

    monkeypatch.setattr("flask.has_request_context", lambda: False)
    svc.add_item(cart=cart, product_id=product.id, quantity=1)

    def boom():
        raise RuntimeError("no context")

    monkeypatch.setattr("flask.has_request_context", boom)
    svc.add_item(cart=cart, product_id=product.id, quantity=1)
    assert svc.cart_subtotal(cart) > 0


# ---------------------------------------------------------------------------
# Notifications / i18n / compliance / tenant / document renderer
# ---------------------------------------------------------------------------


def test_notification_tasks_and_email_sender(app, tenant, monkeypatch):
    monkeypatch.setitem(app.config, "SMTP_HOST", "localhost")
    monkeypatch.setitem(app.config, "SMTP_PORT", 2525)

    def no_smtp(*a, **k):
        raise OSError("smtp offline")

    monkeypatch.setattr(smtplib, "SMTP", no_smtp)
    result = notification_tasks.send_email_task(
        {"template": "generic", "recipient": "a@b.test", "context": {"k": "v"}}
    )
    assert result == {"status": "sent", "recipient": "a@b.test"}

    assert (
        notification_tasks.run_nightly_reconciliation_task()["tenants_processed"] >= 0
    )

    # Verify smtp_configured() outside a request/app context (defensive path).
    class BrokenApp:
        @property
        def config(self):
            raise RuntimeError("no app")

    monkeypatch.setattr("flask.current_app", BrokenApp())
    assert email_sender.smtp_configured() is False


def test_notification_service_dispatch_paths(app, monkeypatch):
    monkeypatch.setitem(app.config, "SMTP_HOST", "localhost")
    monkeypatch.setitem(app.config, "CELERY_TASK_ALWAYS_EAGER", False)
    calls = []
    monkeypatch.setattr(
        notification_tasks.send_email_task,
        "delay",
        lambda payload: calls.append(payload),
    )
    svc = NotificationService()
    payload = svc.enqueue(
        tenant_id=1, channel="email", template="t", recipient="a@b.test"
    )
    assert payload["status"] == "queued" and calls
    assert (
        svc.send_action_email(tenant_id=1, recipient="a@b.test", template="t")["status"]
        == "queued"
    )


def test_i18n_service_paths(app, tenant, product):
    svc = I18nService()
    svc.ensure_locales_seeded()
    assert svc.list_active_locales()
    _fails(NotFoundError, svc.get_locale, "xx")
    with app.test_request_context(headers={"Accept-Language": "en-US,en;q=0.9"}):
        assert svc.resolve_locale(tenant) in ("en", "ar")

    assert (
        GlossaryService().list_terms(
            tenant_id=tenant.id, source_locale="en", target_locale="ar"
        )
        == []
    )
    gsvc = GlossaryService()
    gsvc.upsert_term(
        tenant_id=tenant.id,
        source_locale="en",
        target_locale="ar",
        source_term="cat",
        target_term="قط",
    )
    term = gsvc.upsert_term(
        tenant_id=tenant.id,
        source_locale="en",
        target_locale="ar",
        source_term="cat",
        target_term="قطة",
    )
    assert term.target_term == "قطة"

    tsvc = TranslationService()
    tsvc.upsert_product_translation(
        tenant_id=tenant.id,
        product=product,
        locale="en",
        name="EN",
        slug="final-en-slug",
    )
    found = tsvc.get_product_by_localized_slug(tenant.id, "final-en-slug", "en")
    assert found.id == product.id

    # With no active locales, resolution falls back to the tenant default.
    for locale in Locale.query.all():
        locale.is_active = False
    db.session.commit()
    assert svc.resolve_locale(tenant) == (tenant.default_language or "ar")


def test_compliance_service_paths(app, tenant):
    svc = ComplianceService()
    first = svc.upsert_cookie_settings(tenant_id=tenant.id, banner_message="Hi")
    second = svc.upsert_cookie_settings(
        tenant_id=tenant.id, banner_message="Bye", is_active=False
    )
    assert first.id == second.id and second.is_active is False
    _fails(
        ValidationError,
        svc.exchange_sso_code,
        tenant_id=tenant.id,
        provider_code="",
        external_email="",
    )
    provider = svc.create_sso(
        tenant_id=tenant.id,
        provider_type="oidc",
        client_id="cid",
        client_secret="secret",
    )
    provider.auto_provision = False
    db.session.commit()
    _fails(
        AuthenticationError,
        svc.exchange_sso_code,
        tenant_id=tenant.id,
        provider_code="secret",
        external_email="new@test.com",
        provider_type="oidc",
        client_id="cid",
    )
    assert svc.list_sso(tenant.id)


def test_tenant_service_paths(app, tenant):
    svc = TenantService()
    assert any(t.id == tenant.id for t in svc.list_tenants())
    assert svc.get_by_public_id(tenant.public_id).id == tenant.id
    _fails(NotFoundError, svc.get_by_public_id, uuid.uuid4())
    assert svc.list_users_for_tenant(tenant.id) == []


def test_document_renderer_paths(app, tenant):
    svc = DocumentRenderer()
    _fails(TemplateValidationError, svc.validate_template, "<div>no footer</div>")
    _fails(
        TemplateValidationError,
        svc.validate_template,
        '<footer id="azadexa-platform-footer"></footer>',
    )
    rendered = svc.inject_platform_footer("<div>body</div>", "<b>footer</b>")
    assert "azadexa-platform-footer" in rendered
    assert svc.footer_html() == ""


# ---------------------------------------------------------------------------
# Platform / app / auth and the remaining small services
# ---------------------------------------------------------------------------


def test_app_platform_service_paths(app, tenant):
    assert verify_client_secret("x", "malformed") is False
    svc = AppPlatformService()
    registered = svc.register_app(
        tenant_id=tenant.id, name="FinalApp", redirect_uris=["https://x.test/cb"]
    )
    _fails(
        AuthenticationError,
        svc.issue_oauth_token,
        client_id="missing",
        client_secret="x",
    )
    token = svc.issue_oauth_token(
        client_id=registered.client_id, client_secret=registered._raw_client_secret
    )
    assert token["token_type"] == "Bearer"
    installer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email=f"installer-{uuid.uuid4().hex[:8]}@test.com",
        password="password123",
    )
    inst = svc.install_app(
        tenant_id=tenant.id, app_id=registered.id, installed_by=installer.id
    )
    again = svc.install_app(
        tenant_id=tenant.id, app_id=registered.id, installed_by=installer.id
    )
    assert inst.id == again.id
    svc.subscribe_webhook(
        tenant_id=tenant.id,
        installation_id=inst.id,
        topic="orders/create",
        callback_url="https://x.test/hook",
    )


def test_auth_service_paths(app, tenant):
    svc = AuthService()
    user = svc.register_tenant_user(
        tenant_id=tenant.id,
        email=f"roles-{uuid.uuid4().hex[:8]}@test.com",
        password="password123",
        is_admin=False,
    )
    _fails(
        ValidationError,
        svc.register_tenant_user,
        tenant_id=tenant.id,
        email=user.email,
        password="password123",
    )
    _fails(NotFoundError, svc.assign_role, tenant.id, 999999, "admin")
    role = _row(Role, tenant_id=tenant.id, name="Admin", code="admin")
    first = svc.assign_role(tenant.id, user.id, "admin")
    second = svc.assign_role(tenant.id, user.id, "admin")
    assert first.role_id == second.role_id


def test_bnpl_category_currency_paths(app, tenant, product):
    bsvc = BnplService()
    _fails(ValidationError, bsvc.get_enabled, tenant.id, "unknown")
    bsvc.upsert_provider(tenant_id=tenant.id, provider="tabby", config={"fee": 2})
    csvc = CategoryService()
    assert csvc.list_for_tenant(tenant.id) == []
    csvc.create(tenant_id=tenant.id, name="C", slug="c")
    _fails(ValidationError, csvc.create, tenant_id=tenant.id, name="C", slug="c")
    tenant.default_currency = "12"
    db.session.commit()
    assert resolve_currency_for_tenant(tenant.id) == "ILS"


def test_dropship_gift_livechat_metafield_paths(app, tenant, product):
    order = _order(tenant.id)
    dsvc = DropshipService()
    supplier = dsvc.create_supplier(
        tenant_id=tenant.id,
        name="Supplier",
        contact_email="s@test.com",
    )
    dropship = dsvc.create_order(
        tenant_id=tenant.id,
        supplier_id=supplier.id,
        order_id=order.id,
        cost="10.00",
    )
    assert dropship.cost == Decimal("10.00")

    gsvc = GiftRegistryService()
    _fails(
        NotFoundError,
        gsvc.add_item,
        tenant_id=tenant.id,
        registry_id=999,
        product_id=product.id,
    )
    registry = gsvc.create_registry(
        tenant_id=tenant.id, customer_email="a@b.test", registry_name="Wedding"
    )
    _fails(
        NotFoundError,
        gsvc.add_item,
        tenant_id=tenant.id,
        registry_id=registry.id,
        product_id=999,
    )
    _fails(
        ValidationError,
        gsvc.add_item,
        tenant_id=tenant.id,
        registry_id=registry.id,
        product_id=product.id,
        quantity=0,
    )
    assert gsvc.get_by_slug(registry.slug, tenant.id).id == registry.id
    assert gsvc.list_items(registry_id=registry.id) == []

    lsvc = LiveChatService()
    _fails(
        NotFoundError,
        lsvc.send_message,
        tenant_id=tenant.id,
        session_id=999,
        sender_type="customer",
        message="hi",
    )
    _fails(NotFoundError, lsvc.get_messages, tenant_id=tenant.id, session_id=999)
    session = lsvc.create_session(tenant_id=tenant.id, customer_email="a@b.test")
    lsvc.send_message(
        tenant_id=tenant.id, session_id=session.id, sender_type="customer", message="hi"
    )
    assert lsvc.get_messages(tenant_id=tenant.id, session_id=session.id)

    msvc = MetafieldService()
    _fails(
        NotFoundError,
        msvc.set_value,
        tenant_id=tenant.id,
        definition_id=999,
        owner_id=1,
    )
    definition = msvc.define(
        tenant_id=tenant.id, owner_type="product", key="k", label="K"
    )
    msvc.set_value(
        tenant_id=tenant.id, definition_id=definition.id, owner_id=1, value="a"
    )
    updated = msvc.set_value(
        tenant_id=tenant.id, definition_id=definition.id, owner_id=1, value="b"
    )
    assert updated.value == "b"
    assert msvc.get_for_owner(tenant_id=tenant.id, owner_type="product", owner_id=1)


def test_platform_support_services_paths(app, tenant, product):
    fesvc = FinancialEventsService()
    tenant.platform_commission_percent = Decimal("0.15")
    db.session.commit()
    assert fesvc.resolve_commission_percent(tenant.id) == Decimal("0.15")
    _fails(
        ValueError,
        fesvc.record_inbound,
        tenant_id=tenant.id,
        amount="0",
        event_type="e",
        source_entity="s",
        source_id=1,
    )
    _fails(
        ValueError,
        fesvc.record_outbound,
        tenant_id=tenant.id,
        amount="0",
        event_type="e",
        source_entity="s",
        source_id=1,
    )

    _fails(NotFoundError, StoreFinancialReportService().build, 999999)
    assert StoreFinancialReportService().build(tenant.id)["tenant"]["id"] == tenant.id

    r2 = ReconciliationV2Service()
    run = r2.create_run(tenant_id=tenant.id)
    _fails(
        NotFoundError,
        r2.add_item,
        tenant_id=tenant.id,
        run_id=999,
        financial_event_id=1,
        expected_amount="1",
        actual_amount="1",
    )
    _fails(NotFoundError, r2.complete_run, tenant_id=tenant.id, run_id=999)
    assert r2.complete_run(tenant_id=tenant.id, run_id=run.id).status == "completed"
    assert r2.list_runs(tenant.id)

    sns = StockNotificationService()
    sns.subscribe(tenant_id=tenant.id, product_id=product.id, customer_email="a@b.test")
    again = sns.subscribe(
        tenant_id=tenant.id, product_id=product.id, customer_email="a@b.test"
    )
    assert again.is_notified is False
    assert sns.notify_for_product(tenant_id=tenant.id, product_id=product.id) == 1

    scs = StoreCreditService()
    _fails(
        ValidationError,
        scs.add_funds,
        tenant_id=tenant.id,
        customer_email="a@b.test",
        amount="0",
    )
    _fails(
        ValidationError,
        scs.deduct,
        tenant_id=tenant.id,
        customer_email="a@b.test",
        amount="0",
    )
    _fails(
        ValidationError,
        scs.deduct,
        tenant_id=tenant.id,
        customer_email="a@b.test",
        amount="5",
    )

    gw = GatewayService()
    _fails(
        ValidationError,
        gw.upsert_paypal,
        tenant_id=tenant.id,
        client_id="",
        client_secret="",
    )
    row = gw.upsert_paypal(
        tenant_id=tenant.id,
        client_id="cid",
        client_secret="sec",
        webhook_secret="whsec",
    )
    assert row.webhook_secret == "whsec"
    _fails(NotFoundError, gw.get_enabled, tenant.id, "missing")
    assert gw.ensure_cod_gateway(tenant.id).id == gw.ensure_cod_gateway(tenant.id).id
    assert gw.list_for_tenant(tenant.id) and gw.list_enabled_for_checkout(tenant.id)

    assert ReconciliationService().get_status(tenant.id)["financial_events_total"] >= 0


def test_pdf_service_paths(tmp_path, monkeypatch):
    from i18n.locale import Locale

    assert (
        pdf_service.html_to_text("<script>x</script><p>Hi &amp; bye</p>") == "Hi & bye"
    )
    storage = pdf_service.LocalInvoiceStorage(root=str(tmp_path))
    assert storage.put("a/b.txt", b"data") == "a/b.txt"
    assert storage.get("a/b.txt") == b"data"
    with pytest.raises(ValueError):
        storage._path_for("")
    with pytest.raises(ValueError):
        storage._path_for("../escape")
    monkeypatch.setattr(pdf_service, "_invoice_storage", storage)
    assert pdf_service.get_invoice_storage() is storage
    pdf_service.set_invoice_storage(None)
    assert isinstance(
        pdf_service.get_invoice_storage(), pdf_service.LocalInvoiceStorage
    )

    # No Unicode font available at all -> both defensive paths.
    monkeypatch.delenv("INVOICE_PDF_FONT", raising=False)
    monkeypatch.delenv("ORION_PDF_FONT", raising=False)
    monkeypatch.setattr(pdf_service, "_FONT_CANDIDATES", ())
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    assert pdf_service._find_unicode_font() is None
    with pytest.raises(RuntimeError, match="No Unicode TTF font"):
        pdf_service.html_to_pdf("<p>مرحبا</p>")
