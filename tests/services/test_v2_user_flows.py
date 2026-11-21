"""V2 user flows wired end-to-end at the service/API seam.

Covers: B2B cart pricing, store-credit checkout, gift-registry items and
restock notifications.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from gift_svc.gift_registry_service import GiftRegistryService
from stock_notification_svc.stock_notification_service import StockNotificationService
from store_credit.store_credit import StoreCreditTransaction
from store_credit_svc.store_credit_service import StoreCreditService
from support.http import auth_headers

from auth.auth_service import AuthService
from b2b_svc.b2b_service import B2bService
from catalog_svc.product_service import ProductService
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def tenant(app):
    return TenantService().create_tenant(
        name="V2 Flows", slug="v2-flows", email="flows@test.com"
    )


@pytest.fixture
def product(tenant):
    return ProductService().create(
        tenant_id=tenant.id,
        name="Flow Widget",
        slug="flow-widget",
        price="100.00",
        quantity=20,
        is_published=True,
    )


# ---------------------------------------------------------------------------
# (أ) B2B pricing in the cart
# ---------------------------------------------------------------------------


def test_cart_uses_b2b_group_price_for_member(app, tenant, product):
    user = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="wholesale@flows.test",
        password="password123",
        is_admin=False,
    )
    b2b = B2bService()
    group = b2b.create_customer_group(
        tenant_id=tenant.id,
        name="VIP Wholesale",
        code="vip-wholesale",
        discount_percent="10",
    )
    b2b.add_group_member(tenant_id=tenant.id, group_id=group.id, user_id=user.id)

    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    item = CartService().add_item(
        cart=cart, product_id=product.id, quantity=2, user_id=user.id
    )

    assert item.unit_price == Decimal("90.00")
    assert item.total_price == Decimal("180.00")


def test_cart_uses_catalog_price_without_group_context(app, tenant, product):
    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    item = CartService().add_item(cart=cart, product_id=product.id, quantity=1)

    assert item.unit_price == product.price


def test_cart_reprices_existing_item_for_group_member(app, tenant, product):
    user = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="member@flows.test",
        password="password123",
        is_admin=False,
    )
    b2b = B2bService()
    group = b2b.create_customer_group(
        tenant_id=tenant.id,
        name="Silver",
        code="silver",
        discount_percent="5",
    )
    b2b.add_group_member(tenant_id=tenant.id, group_id=group.id, user_id=user.id)

    carts = CartService()
    cart = carts.get_or_create_cart(tenant_id=tenant.id)
    carts.add_item(cart=cart, product_id=product.id, quantity=1)
    item = carts.add_item(cart=cart, product_id=product.id, quantity=1, user_id=user.id)

    assert item.quantity == 2
    assert item.unit_price == Decimal("95.00")
    assert item.total_price == Decimal("190.00")


# ---------------------------------------------------------------------------
# (ب) Store credit at checkout
# ---------------------------------------------------------------------------


def _cart_with_item(tenant, product, quantity=1):
    carts = CartService()
    cart = carts.get_or_create_cart(tenant_id=tenant.id)
    carts.add_item(cart=cart, product_id=product.id, quantity=quantity)
    return cart


def test_checkout_deducts_store_credit_and_records_transaction(app, tenant, product):
    credits = StoreCreditService()
    credits.add_funds(
        tenant_id=tenant.id, customer_email="buyer@flows.test", amount="50.00"
    )
    cart = _cart_with_item(tenant, product, quantity=2)  # 200.00 subtotal

    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@flows.test",
        shipping_address={},
        use_store_credit=True,
    )

    assert order.total == Decimal("150.00")
    assert order.payment_status == "partially_paid"
    assert credits.get_balance(
        tenant_id=tenant.id, customer_email="buyer@flows.test"
    ) == Decimal("0.00")

    txn = StoreCreditTransaction.query.filter_by(
        reference_type="order", reference_id=order.id
    ).first()
    assert txn is not None
    assert txn.transaction_type == "debit"
    assert txn.amount == Decimal("50.00")
    assert txn.balance_after == Decimal("0.00")


def test_checkout_store_credit_can_cover_full_total(app, tenant, product):
    credits = StoreCreditService()
    credits.add_funds(
        tenant_id=tenant.id, customer_email="buyer@flows.test", amount="500.00"
    )
    cart = _cart_with_item(tenant, product)

    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@flows.test",
        shipping_address={},
        use_store_credit=True,
    )

    assert order.total == Decimal("0.00")
    assert order.payment_status == "paid"
    assert credits.get_balance(
        tenant_id=tenant.id, customer_email="buyer@flows.test"
    ) == Decimal("400.00")


def test_checkout_leaves_store_credit_untouched_by_default(app, tenant, product):
    credits = StoreCreditService()
    credits.add_funds(
        tenant_id=tenant.id, customer_email="buyer@flows.test", amount="50.00"
    )
    cart = _cart_with_item(tenant, product)

    order = CheckoutService().checkout(
        cart=cart,
        customer_email="buyer@flows.test",
        shipping_address={},
    )

    assert order.total == Decimal("100.00")
    assert order.payment_status == "pending"
    assert credits.get_balance(
        tenant_id=tenant.id, customer_email="buyer@flows.test"
    ) == Decimal("50.00")
    assert StoreCreditTransaction.query.filter_by(reference_type="order").count() == 0


# ---------------------------------------------------------------------------
# (ج) Gift-registry item endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def registry_api(app, tenant, product):
    from feature_flag_svc.feature_flag_service import FeatureFlagService

    from platform_svc.platform_settings_service import PlatformSettingsService

    PlatformSettingsService().ensure_seeded()
    FeatureFlagService().ensure_seeded()

    auth = AuthService()
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="staff@flows.test",
        password="password123",
        is_admin=True,
    )
    owner = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="owner@flows.test",
        password="password123",
        is_admin=False,
    )
    outsider = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="outsider@flows.test",
        password="password123",
        is_admin=False,
    )
    registry = GiftRegistryService().create_registry(
        tenant_id=tenant.id,
        customer_email=owner.email,
        registry_name="Wedding",
        event_type="wedding",
        is_public=True,
    )
    return {
        "tenant": tenant,
        "product": product,
        "registry": registry,
        "staff": auth_headers(admin, app=app, tenant_id=tenant.slug),
        "owner": auth_headers(owner, app=app, tenant_id=tenant.slug),
        "outsider": auth_headers(outsider, app=app, tenant_id=tenant.slug),
        "anonymous": {"X-Tenant-ID": tenant.slug},
    }


def test_gift_registry_items_can_be_added_and_viewed(client, registry_api):
    slug = registry_api["registry"].slug
    product_id = registry_api["product"].id

    created = client.post(
        f"/api/v1/gift-registries/{slug}/items",
        headers=registry_api["staff"],
        json={"product_id": product_id, "quantity": 2},
    )
    assert created.status_code == 201, created.get_json()
    assert created.get_json()["item"]["requested_quantity"] == 2

    listed = client.get(
        f"/api/v1/gift-registries/{slug}/items", headers=registry_api["owner"]
    )
    assert listed.status_code == 200, listed.get_json()
    payload = listed.get_json()
    assert payload["registry"]["slug"] == slug
    assert len(payload["items"]) == 1
    assert payload["items"][0]["product_id"] == product_id


def test_gift_registry_items_deny_anonymous_and_non_owner(client, registry_api):
    url = f"/api/v1/gift-registries/{registry_api['registry'].slug}/items"
    body = {"product_id": registry_api["product"].id, "quantity": 1}

    assert client.get(url, headers=registry_api["anonymous"]).status_code == 401
    assert (
        client.post(url, headers=registry_api["anonymous"], json=body).status_code
        == 401
    )
    assert client.get(url, headers=registry_api["outsider"]).status_code == 403
    assert (
        client.post(url, headers=registry_api["outsider"], json=body).status_code == 403
    )


# ---------------------------------------------------------------------------
# (د) Restock notifications
# ---------------------------------------------------------------------------


def test_restock_from_zero_notifies_subscribers(app, tenant):
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Restock Item",
        slug="restock-item",
        price="15.00",
        quantity=0,
        is_published=True,
    )
    notification = StockNotificationService().subscribe(
        tenant_id=tenant.id,
        product_id=product.id,
        customer_email="waiting@flows.test",
    )

    ProductService().update(product, quantity=5)

    db.session.refresh(notification)
    assert notification.is_notified is True
    assert notification.notified_at is not None


def test_restock_notification_ignores_non_restock_updates(app, tenant):
    product = ProductService().create(
        tenant_id=tenant.id,
        name="In Stock Item",
        slug="in-stock-item",
        price="15.00",
        quantity=5,
        is_published=True,
    )
    notification = StockNotificationService().subscribe(
        tenant_id=tenant.id,
        product_id=product.id,
        customer_email="waiting@flows.test",
    )

    ProductService().update(product, quantity=10)

    db.session.refresh(notification)
    assert notification.is_notified is False
