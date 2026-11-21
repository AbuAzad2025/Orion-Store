from __future__ import annotations

import pytest
from accessibility_svc.accessibility_service import AccessibilityService
from affiliate_svc.affiliate_service import AffiliateService
from app_platform_svc.app_platform_service import AppPlatformService
from audit_svc.audit_v2_service import AuditV2Service
from bopis_svc.bopis_service import BopisService
from bundle_svc.bundle_service import BundleService
from compliance_svc.compliance_service import ComplianceService
from currency_svc.currency_service import CurrencyService
from draft_order_svc.draft_order_service import DraftOrderService
from dropship_svc.dropship_service import DropshipService
from feature_flag_svc.feature_flag_service import FeatureFlagService
from fraud_svc.fraud_service import FraudService
from gift_svc.gift_registry_service import GiftRegistryService
from import_export_svc.import_export_service import ImportExportService
from live_chat_svc.live_chat_service import LiveChatService
from metafield_svc.metafield_service import MetafieldService
from reconciliation_svc.reconciliation_v2_service import ReconciliationV2Service
from schema_markup_svc.schema_markup_service import SchemaMarkupService
from search_svc.search_merchandising_service import SearchMerchandisingService
from stock_notification_svc.stock_notification_service import StockNotificationService
from store_credit_svc.store_credit_service import StoreCreditService
from subscription_svc.subscription_service import SubscriptionService
from tax_svc.tax_service import TaxService
from workflow_svc.workflow_service import WorkflowService

from catalog_svc.product_service import ProductService
from oms_svc.extensions.inventory_transfer_service import InventoryTransferService
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def tenant(app):
    return TenantService().create_tenant(
        name="V2 Test", slug="v2-test", email="v2@test.com"
    )


@pytest.fixture
def product(tenant):
    from catalog.brand import Brand
    from catalog.category import Category
    from catalog.product import Product

    brand = Brand(name="TestBrand", slug="test-brand", tenant_id=tenant.id)
    cat = Category(name="TestCat", slug="test-cat", tenant_id=tenant.id)
    db.session.add_all([brand, cat])
    db.session.commit()
    prod = Product(
        name="Test Product",
        slug="test-product",
        tenant_id=tenant.id,
        price="29.99",
        quantity=100,
        is_published=True,
        brand_id=brand.id,
        category_id=cat.id,
    )
    db.session.add(prod)
    db.session.commit()
    return prod


def test_subscription_plan_crud(tenant):
    svc = SubscriptionService()
    plan = svc.create_plan(
        tenant_id=tenant.id,
        name="Pro",
        code="pro",
        billing_period_days=30,
        price="29.99",
        trial_period_days=14,
    )
    assert plan.name == "Pro"
    assert plan.code == "pro"
    assert float(plan.price) == 29.99
    assert plan.billing_period_days == 30
    assert plan.trial_period_days == 14


def test_subscription_subscribe(tenant):
    subs = SubscriptionService()
    plan = subs.create_plan(
        tenant_id=tenant.id,
        name="Pro",
        code="pro",
        billing_period_days=30,
        price="29.99",
    )
    sub = subs.subscribe(
        tenant_id=tenant.id, plan_id=plan.id, customer_email="cust@test.com"
    )
    assert sub.customer_email == "cust@test.com"
    assert sub.status == "active"


def test_store_credit_add_and_deduct(tenant):
    svc = StoreCreditService()
    credit = svc.add_funds(
        tenant_id=tenant.id,
        customer_email="buyer@test.com",
        amount="50.00",
        reason="Promotion",
    )
    assert float(credit.balance) == 50.00

    credit = svc.deduct(
        tenant_id=tenant.id, customer_email="buyer@test.com", amount="20.00"
    )
    assert float(credit.balance) == 30.00

    balance = svc.get_balance(tenant_id=tenant.id, customer_email="buyer@test.com")
    assert float(balance) == 30.00


def test_draft_order_lifecycle(tenant, product):
    svc = DraftOrderService()
    draft = svc.create_draft(tenant_id=tenant.id, notes="Draft order")
    assert draft.status == "draft"
    assert draft.notes == "Draft order"

    item = svc.add_item(
        tenant_id=tenant.id, draft_id=draft.id, product_id=product.id, quantity=2
    )
    assert item.quantity == 2

    order = svc.convert_to_order(
        tenant_id=tenant.id, draft_id=draft.id, customer_email="cust@test.com"
    )
    assert order.status == "pending"


def test_tax_rate_lookup(tenant):
    svc = TaxService()
    jur = svc.create_jurisdiction(
        tenant_id=tenant.id,
        name="CA State",
        code="CA-STATE",
        country_code="US",
        region="CA",
    )
    assert jur.name == "CA State"

    rate = svc.set_rate(tenant_id=tenant.id, jurisdiction_id=jur.id, rate="0.0725")
    assert float(rate.rate) == 0.0725


def test_bundle_crud(tenant, product):
    svc = BundleService()
    bundle = svc.create_bundle(
        tenant_id=tenant.id, name="Combo", slug="combo-1", bundle_price="5.00"
    )
    assert bundle.name == "Combo"
    assert float(bundle.bundle_price) == 5.00


def test_metafield_crud(tenant):
    svc = MetafieldService()
    mf = svc.define(
        tenant_id=tenant.id,
        owner_type="product",
        key="material",
        label="Material",
        field_type="string",
    )
    assert mf.key == "material"

    val = svc.set_value(
        tenant_id=tenant.id, definition_id=mf.id, owner_id=1, value="cotton"
    )
    assert val.value == "cotton"


def test_pickup_location(tenant):
    svc = BopisService()
    loc = svc.create_location(
        tenant_id=tenant.id,
        code="DTLA",
        name="Downtown Store",
        address={
            "street": "123 Main St",
            "city": "LA",
            "region": "CA",
            "postal_code": "90001",
            "country": "US",
        },
    )
    assert loc.name == "Downtown Store"


def test_currency_rate():
    svc = CurrencyService()
    rate = svc.set_rate(from_currency="USD", to_currency="EUR", rate="0.85")
    assert float(rate.rate) == 0.85

    fetched = svc.latest_rate(from_currency="USD", to_currency="EUR")
    assert float(fetched) == 0.85


def test_create_job(tenant):
    svc = ImportExportService()
    job = svc.create_job(tenant_id=tenant.id, job_type="export", entity_type="products")
    assert job.job_type == "export"
    assert job.status == "pending"


def test_stock_notification(tenant, product):
    svc = StockNotificationService()
    sn = svc.subscribe(
        tenant_id=tenant.id, customer_email="notify@test.com", product_id=product.id
    )
    assert sn.customer_email == "notify@test.com"
    assert sn.product_id == product.id
    assert sn.is_notified is False


def test_app_platform_lifecycle(tenant):
    svc = AppPlatformService()
    app = svc.register_app(
        tenant_id=tenant.id,
        name="MyApp",
        redirect_uris=["https://app.com/callback"],
        scopes="read_products write_products",
    )
    assert app.name == "MyApp"

    sandbox = svc.create_sandbox(
        tenant_id=tenant.id,
        slug="test-sandbox",
        name="Test Sandbox",
        expires_at="2027-01-01",
    )
    assert sandbox.slug.startswith("test-sandbox")


def test_fraud_review(tenant):
    from order.order import Order

    order = Order(
        tenant_id=tenant.id,
        order_number="FRAUD-TEST-1",
        customer_email="fraud@test.com",
        shipping_address={},
        subtotal="10",
        total="10",
    )
    db.session.add(order)
    db.session.commit()

    svc = FraudService()
    review = svc.review_order(tenant_id=tenant.id, order_id=order.id, risk_score=85)
    assert review.order_id == order.id
    assert review.risk_score == 85


def test_consent_and_data_request(tenant):
    svc = ComplianceService()
    c = svc.record_consent(
        tenant_id=tenant.id,
        customer_email="user@test.com",
        consent_type="marketing",
        granted=True,
    )
    assert c.customer_email == "user@test.com"
    assert c.consent_type == "marketing"
    assert c.granted is True

    req = svc.create_data_request(
        tenant_id=tenant.id, customer_email="user@test.com", request_type="access"
    )
    assert req.request_type == "access"


def test_workflow_definition(tenant):
    svc = WorkflowService()
    wf = svc.create_definition(
        tenant_id=tenant.id,
        name="OrderConfirmation",
        trigger_event="order.placed",
        actions=[{"type": "send_email", "template": "order_confirmation"}],
    )
    assert wf.name == "OrderConfirmation"
    assert wf.trigger_event == "order.placed"


def test_synonym_and_boost(tenant):
    svc = SearchMerchandisingService()
    s = svc.add_synonym(
        tenant_id=tenant.id, term="laptop", synonyms=["notebook", "ultrabook"]
    )
    assert s.term == "laptop"
    assert "notebook" in s.synonyms


def test_affiliate_program(tenant):
    svc = AffiliateService()
    prog = svc.create_program(
        tenant_id=tenant.id,
        name="Gold Partners",
        code="GOLD",
        commission_type="percentage",
        commission_value="15.00",
        cookie_days=30,
    )
    assert prog.name == "Gold Partners"
    assert float(prog.commission_value) == 15.00


def test_gift_registry(tenant):
    svc = GiftRegistryService()
    r = svc.create_registry(
        tenant_id=tenant.id,
        customer_email="gifter@test.com",
        registry_name="Wedding",
        event_type="wedding",
        is_public=True,
    )
    assert r.registry_name == "Wedding"
    assert r.event_type == "wedding"
    assert r.is_public is True
    assert r.slug is not None and len(r.slug) > 0


def test_dropship_supplier(tenant):
    svc = DropshipService()
    s = svc.create_supplier(
        tenant_id=tenant.id,
        name="FastShip Inc",
        contact_email="orders@fastship.com",
        fulfillment_time_days=3,
    )
    assert s.name == "FastShip Inc"
    assert s.fulfillment_time_days == 3


def test_schema_markup(tenant, product):
    svc = SchemaMarkupService()
    m = svc.set_markup(
        tenant_id=tenant.id,
        product_id=product.id,
        schema_type="Product",
        json_ld={"name": "Test Product", "price": "29.99"},
    )
    assert m.schema_type == "Product"

    fetched = svc.get_markup(tenant_id=tenant.id, product_id=product.id)
    assert fetched is not None


def test_accessibility_audit(tenant):
    svc = AccessibilityService()
    audit = svc.record_audit(
        tenant_id=tenant.id,
        page_url="/products",
        score=92,
        issues={"contrast": ["low contrast on button"]},
    )
    assert audit.page_url == "/products"
    assert audit.score == 92


def test_live_chat_session(tenant):
    svc = LiveChatService()
    session = svc.create_session(tenant_id=tenant.id, customer_email="chat@test.com")
    assert session.status == "pending"

    msg = svc.send_message(
        tenant_id=tenant.id,
        session_id=session.id,
        sender_type="customer",
        message="Hello!",
    )
    assert msg.message == "Hello!"
    assert msg.sender_type == "customer"

    messages = svc.get_messages(tenant_id=tenant.id, session_id=session.id)
    assert len(messages) == 1


def test_reconciliation_run(tenant):
    from platform_svc.financial_events_service import FinancialEventsService

    event = FinancialEventsService().record_inbound(
        tenant_id=tenant.id,
        amount="100.00",
        event_type="test.reconciliation",
        source_entity="test",
        source_id=1,
        apply_commission=False,
    )
    svc = ReconciliationV2Service()
    run = svc.create_run(tenant_id=tenant.id)
    assert run.status == "pending"

    item = svc.add_item(
        tenant_id=tenant.id,
        run_id=run.id,
        financial_event_id=event.id,
        expected_amount="100.00",
        actual_amount="100.00",
    )
    assert float(item.expected_amount) == 100.00
    assert float(item.actual_amount) == 100.00

    completed = svc.complete_run(run_id=run.id, tenant_id=tenant.id)
    assert completed.status == "completed"


def test_audit_log_and_report():
    from auth.auth_service import AuthService

    user = AuthService().register_super_admin(
        email="audit@test.com", password="password123"
    )
    svc = AuditV2Service()
    log = svc.log_action(
        user_id=user.id, action="user.login", details={"ip": "192.168.1.1"}
    )
    assert log.action == "user.login"

    report = svc.create_report(
        report_type="security_review",
        generated_by=user.id,
        summary={"findings": []},
    )
    assert report.report_type == "security_review"


def test_inventory_transfer(tenant):
    svc = InventoryTransferService()
    from oms.warehouse import Warehouse

    wh1 = Warehouse(name="WH1", tenant_id=tenant.id, code="WH1")
    wh2 = Warehouse(name="WH2", tenant_id=tenant.id, code="WH2")
    db.session.add_all([wh1, wh2])
    db.session.commit()

    transfer = svc.create_transfer(
        tenant_id=tenant.id, from_warehouse_id=wh1.id, to_warehouse_id=wh2.id
    )
    assert transfer.status == "draft"
    assert transfer.from_warehouse_id == wh1.id
    assert transfer.to_warehouse_id == wh2.id


def test_rollout_evaluation(tenant):
    svc = FeatureFlagService()
    svc.ensure_seeded()
    flag = svc.get_by_code("draft_orders_enabled")
    assert flag.rollout_percent == 100
