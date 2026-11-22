"""Final pass coverage for the last uncovered v1 API / core lines.

Every test drives a real Flask route through the test client and persists real
rows in the PostgreSQL test database. No service, ORM or request behaviour is
mocked: each branch is reached with genuine prerequisites and payloads.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from dropship_svc.dropship_service import DropshipService
from gift_svc.gift_registry_service import GiftRegistryService
from subscription_svc.subscription_service import SubscriptionService
from support.http import auth_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from order.order import Order, OrderItem
from orion.extensions import db
from payment.payment import Payment
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def api_ctx(app):
    """A real tenant with a tenant admin, a customer and a purchasable product."""
    tenant = TenantService().create_tenant(
        name="Final API Tenant",
        slug="final-api-tenant",
        email="final@tenant.test",
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="admin@final.test",
        password="password123",
        is_admin=True,
    )
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="buyer@final.test",
        password="password123",
        is_admin=False,
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Final Product",
        slug="final-product",
        price="40.00",
        quantity=10,
        is_published=True,
    )
    return SimpleNamespace(
        tenant=tenant,
        admin=admin,
        customer=customer,
        product=product,
        admin_headers=auth_headers(admin, app=app, tenant_id=tenant.slug),
        customer_headers=auth_headers(customer, app=app, tenant_id=tenant.slug),
        # A signed JWT with a legacy (non-UUID) identity: @jwt_required() accepts
        # it, but the middleware cannot bind a User to the request context.
        legacy_headers=auth_headers(
            "legacy-slug-identity", app=app, tenant_id=tenant.slug
        ),
    )


def _make_order(tenant_id: int, *, total: str = "80.00") -> Order:
    order = Order(
        tenant_id=tenant_id,
        order_number=f"FINAL-{uuid.uuid4().hex[:10]}",
        status="pending",
        payment_status="pending",
        fulfillment_status="unfulfilled",
        customer_email="buyer@final.test",
        customer_first_name="Final",
        customer_last_name="Buyer",
        is_guest=True,
        shipping_address={},
        subtotal=total,
        tax_amount="0",
        shipping_cost="0",
        discount_amount="0",
        total=total,
    )
    db.session.add(order)
    db.session.commit()
    return order


def _make_order_item(order: Order, product, *, total: str = "40.00") -> OrderItem:
    item = OrderItem(
        order_id=order.id,
        tenant_id=order.tenant_id,
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        unit_price=product.price,
        quantity=1,
        total_price=total,
    )
    db.session.add(item)
    db.session.commit()
    return item


# ---------------------------------------------------------------------------
# customer_flows.py:19 — _ctx() rejects a JWT that has no bound User
# ---------------------------------------------------------------------------


def test_customer_flows_rejects_token_without_bound_user(client, api_ctx):
    resp = client.get("/api/v1/store/account/plans", headers=api_ctx.legacy_headers)
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Authentication required."


# ---------------------------------------------------------------------------
# customer_flows.py:190-191 — invalid product id on the customer registry item
# ---------------------------------------------------------------------------


def test_customer_flows_add_registry_item_invalid_product_id(client, api_ctx):
    registry = GiftRegistryService().create_registry(
        tenant_id=api_ctx.tenant.id,
        customer_email=api_ctx.customer.email,
        registry_name="Final Customer Registry",
        user_id=api_ctx.customer.id,
    )
    resp = client.post(
        f"/api/v1/store/account/gift-registries/{registry.slug}/items",
        headers=api_ctx.customer_headers,
        json={"product_id": "not-an-int"},
    )
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Invalid request."}


# ---------------------------------------------------------------------------
# gift_registries.py:93-94 — invalid product id on the staff registry item route
# ---------------------------------------------------------------------------


def test_gift_registry_add_item_invalid_product_id(client, api_ctx):
    registry = GiftRegistryService().create_registry(
        tenant_id=api_ctx.tenant.id,
        customer_email=api_ctx.admin.email,
        registry_name="Final Staff Registry",
        user_id=api_ctx.admin.id,
    )
    resp = client.post(
        f"/api/v1/gift-registries/{registry.slug}/items",
        headers=api_ctx.admin_headers,
        json={"product_id": "not-an-int"},
    )
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Invalid request."}


# ---------------------------------------------------------------------------
# subscriptions.py:121 — digital asset download creation (real asset + order)
# ---------------------------------------------------------------------------


def test_subscriptions_create_digital_asset_download(client, api_ctx):
    order = _make_order(api_ctx.tenant.id)
    asset = SubscriptionService().create_digital_asset(
        tenant_id=api_ctx.tenant.id,
        product_id=api_ctx.product.id,
        file_url="https://example.test/files/guide.pdf",
        file_name="guide.pdf",
        mime_type="application/pdf",
        max_downloads=5,
    )
    resp = client.post(
        f"/api/v1/subscriptions/digital-assets/{asset.id}/download",
        headers=api_ctx.admin_headers,
        json={"order_id": order.id},
    )
    assert resp.status_code == 201
    download = resp.get_json()["download"]
    assert download["asset_id"] == asset.id
    assert download["order_id"] == order.id
    assert download["download_count"] == 0


# ---------------------------------------------------------------------------
# subscriptions.py:138 — license generation (real order item + product)
# ---------------------------------------------------------------------------


def test_subscriptions_generate_license(client, api_ctx):
    order = _make_order(api_ctx.tenant.id)
    item = _make_order_item(order, api_ctx.product)
    resp = client.post(
        "/api/v1/subscriptions/licenses",
        headers=api_ctx.admin_headers,
        json={"order_item_id": item.id, "product_id": api_ctx.product.id},
    )
    assert resp.status_code == 201
    license_key = resp.get_json()["license"]
    assert license_key["key"].startswith("LIC-")
    assert license_key["order_item_id"] == item.id
    assert license_key["product_id"] == api_ctx.product.id


# ---------------------------------------------------------------------------
# tenant_portal.py:234 — successful payment refund (real completed payment)
# ---------------------------------------------------------------------------


def test_tenant_portal_refund_payment_success(client, api_ctx):
    order = _make_order(api_ctx.tenant.id)
    payment = Payment(
        tenant_id=api_ctx.tenant.id,
        order_id=order.id,
        amount=Decimal("80.00"),
        currency="ILS",
        payment_method="cod",
        payment_provider="cod",
        status="completed",
    )
    db.session.add(payment)
    db.session.commit()

    resp = client.post(
        f"/api/v1/tenant/payments/{payment.public_id}/refund",
        headers=api_ctx.admin_headers,
        json={"reason": "final coverage"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["refund"]["status"] == "completed"
    assert resp.get_json()["refund"]["amount"] == "80.00"
    db.session.refresh(payment)
    assert payment.status == "refunded"


# ---------------------------------------------------------------------------
# dropship.py:89 — dropship order creation (real supplier + order)
# ---------------------------------------------------------------------------


def test_dropship_create_order_success(client, api_ctx):
    order = _make_order(api_ctx.tenant.id)
    supplier = DropshipService().create_supplier(
        tenant_id=api_ctx.tenant.id,
        name="Final Supplier",
        contact_email="supplier@final.test",
        fulfillment_time_days=3,
    )
    resp = client.post(
        "/api/v1/dropship/orders",
        headers=api_ctx.admin_headers,
        json={
            "supplier_id": supplier.id,
            "order_id": order.id,
            "cost": "12.50",
        },
    )
    assert resp.status_code == 201
    created = resp.get_json()["dropship_order"]
    assert created["supplier_id"] == supplier.id
    assert created["order_id"] == order.id
    assert created["cost"] == "12.50"
