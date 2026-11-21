"""Coverage for the customer self-service and storefront helper modules."""

from __future__ import annotations

import pytest
from support.http import auth_headers, tenant_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def store(app):
    tenant = TenantService().create_tenant(
        name="Flow Store", slug="flow-store", email="flow@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Flow Product",
        slug="flow-product",
        price="20.00",
        quantity=10,
        is_published=True,
    )
    auth = AuthService()
    customer = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="buyer@flow.com",
        password="password123",
        is_admin=False,
    )
    admin = auth.register_tenant_user(
        tenant_id=tenant.id,
        email="admin@flow.com",
        password="password123",
        is_admin=True,
    )
    return tenant, product, customer, admin


def _plan(app, tenant_id):
    from subscription_svc.subscription_service import SubscriptionService

    return SubscriptionService().create_plan(
        tenant_id=tenant_id,
        name="Gold",
        code="gold",
        billing_period_days=30,
        price="9.99",
    )


def test_customer_service_flows(client, store):
    tenant, product, customer, _admin = store
    headers = auth_headers(customer, tenant_id=tenant.slug)
    _plan(client.app, tenant.id)

    plans = client.get("/api/v1/store/account/plans", headers=headers)
    assert plans.status_code == 200
    assert plans.get_json()["plans"]

    sub = client.post(
        "/api/v1/store/account/subscribe",
        headers=headers,
        json={"plan_id": plans.get_json()["plans"][0]["id"]},
    )
    assert sub.status_code == 201

    credit = client.get("/api/v1/store/account/credit", headers=headers)
    assert credit.status_code == 200
    assert "balance" in credit.get_json()["credit"]

    quote = client.post(
        "/api/v1/store/account/quote-requests",
        headers=headers,
        json={"product_id": product.id, "quantity": 2, "notes": "bulk"},
    )
    assert quote.status_code == 201
    assert (
        client.get("/api/v1/store/account/quote-requests", headers=headers).status_code
        == 200
    )

    registry = client.post(
        "/api/v1/store/account/gift-registries",
        headers=headers,
        json={"registry_name": "Wedding", "event_type": "wedding"},
    )
    assert registry.status_code == 201
    slug = registry.get_json()["registry"]["slug"]
    assert (
        client.get("/api/v1/store/account/gift-registries", headers=headers).status_code
        == 200
    )
    item = client.post(
        f"/api/v1/store/account/gift-registries/{slug}/items",
        headers=headers,
        json={"product_id": product.id},
    )
    assert item.status_code == 201


def test_platform_user_management(client, store, platform_admin_headers):
    tenant, _product, _customer, _admin = store
    headers = platform_admin_headers
    created = client.post(
        "/api/v1/users/",
        headers=headers,
        json={
            "email": "new-admin@flow.com",
            "password": "password123",
            "tenant_id": tenant.id,
            "is_admin": True,
        },
    )
    assert created.status_code == 201
    user_id = created.get_json()["user"]["id"]
    assert client.get("/api/v1/users/", headers=headers).status_code == 200
    assert (
        client.put(
            f"/api/v1/users/{user_id}", headers=headers, json={"first_name": "New"}
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/users/{user_id}", headers=headers).status_code == 200


def test_gdpr_self_service(client, store):
    tenant, _product, customer, _admin = store
    headers = auth_headers(customer, tenant_id=tenant.slug)
    created = client.post(
        "/api/v1/store/account/data-requests",
        headers=headers,
        json={"request_type": "export"},
    )
    assert created.status_code == 201
    req_id = created.get_json()["request"]["id"]
    exported = client.get(
        f"/api/v1/store/account/data-requests/{req_id}/export", headers=headers
    )
    assert exported.status_code == 200
    assert exported.get_json()["subject"]["email"] == customer.email

    deletion = client.post(
        "/api/v1/store/account/data-requests",
        headers=headers,
        json={"request_type": "delete"},
    )
    assert deletion.status_code == 201
    delete_id = deletion.get_json()["request"]["id"]
    executed = client.post(
        f"/api/v1/store/account/data-requests/{delete_id}/delete",
        headers=headers,
        json={},
    )
    assert executed.status_code == 200
    assert executed.get_json()["request"]["status"] == "completed"


def test_admin_subscription_and_oms_flows(client, store):
    tenant, product, customer, admin = store
    headers = auth_headers(admin, tenant_id=tenant.slug)

    plan = client.post(
        "/api/v1/subscriptions/plans",
        headers=headers,
        json={"name": "Pro", "code": "pro", "billing_period_days": 30, "price": "5.00"},
    )
    assert plan.status_code == 201
    assert client.get("/api/v1/subscriptions/plans", headers=headers).status_code == 200
    sub = client.post(
        "/api/v1/subscriptions/subscribe",
        headers=headers,
        json={
            "plan_id": plan.get_json()["plan"]["id"],
            "customer_email": customer.email,
        },
    )
    assert sub.status_code == 201
    assert (
        client.get("/api/v1/subscriptions/subscriptions", headers=headers).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/subscriptions/subscriptions/{sub.get_json()['subscription']['id']}/cancel",
            headers=headers,
        ).status_code
        == 200
    )

    wh1 = client.post(
        "/api/v1/oms/warehouses", headers=headers, json={"name": "A", "code": "a"}
    )
    wh2 = client.post(
        "/api/v1/oms/warehouses", headers=headers, json={"name": "B", "code": "b"}
    )
    assert wh1.status_code == 201 and wh2.status_code == 201
    assert (
        client.put(
            "/api/v1/oms/inventory",
            headers=headers,
            json={
                "warehouse_id": wh1.get_json()["warehouse"]["id"],
                "product_id": product.id,
                "quantity": 5,
            },
        ).status_code
        == 200
    )
    transfer = client.post(
        "/api/v1/oms-ext/transfers",
        headers=headers,
        json={
            "from_warehouse_id": wh1.get_json()["warehouse"]["id"],
            "to_warehouse_id": wh2.get_json()["warehouse"]["id"],
        },
    )
    assert transfer.status_code == 201
    transfer_id = transfer.get_json()["transfer"]["id"]
    assert client.get("/api/v1/oms-ext/transfers", headers=headers).status_code == 200
    assert (
        client.post(
            f"/api/v1/oms-ext/transfers/{transfer_id}/items",
            headers=headers,
            json={"product_id": product.id, "quantity": 2},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/oms-ext/transfers/{transfer_id}/complete", headers=headers
        ).status_code
        == 200
    )


def test_admin_catalog_tax_bopis_and_credit(client, store):
    tenant, product, customer, admin = store
    headers = auth_headers(admin, tenant_id=tenant.slug)

    bundle = client.post(
        "/api/v1/bundles",
        headers=headers,
        json={"name": "Starter", "slug": "starter", "bundle_price": "9.00"},
    )
    assert bundle.status_code == 201
    assert client.get("/api/v1/bundles", headers=headers).status_code == 200

    location = client.post(
        "/api/v1/bopis/locations",
        headers=headers,
        json={
            "code": "main",
            "name": "Main",
            "address": {"text": "Center"},
            "phone": "123",
        },
    )
    assert location.status_code == 201
    assert client.get("/api/v1/bopis/locations", headers=headers).status_code == 200
    slot = client.post(
        f"/api/v1/bopis/locations/{location.get_json()['location']['id']}/slots",
        headers=headers,
        json={"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"},
    )
    assert slot.status_code == 201

    jurisdiction = client.post(
        "/api/v1/tax/jurisdictions",
        headers=headers,
        json={
            "code": "PS-WB",
            "name": "West Bank",
            "country_code": "PS",
            "region": "WB",
        },
    )
    assert jurisdiction.status_code == 201
    jid = jurisdiction.get_json()["jurisdiction"]["id"]
    assert (
        client.post(
            f"/api/v1/tax/jurisdictions/{jid}/rates",
            headers=headers,
            json={"rate": "0.16"},
        ).status_code
        == 201
    )
    preview = client.post(
        "/api/v1/tax/calculate",
        headers=tenant_headers(tenant.slug),
        json={
            "subtotal": "100.00",
            "shipping_address": {"country_code": "PS", "region": "WB"},
        },
    )
    assert preview.status_code == 200

    assert (
        client.get(
            f"/api/v1/store-credit/balance?customer_email={customer.email}",
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/store-credit/add",
            headers=headers,
            json={"customer_email": customer.email, "amount": "10.00"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/store-credit/transactions?customer_email={customer.email}",
            headers=headers,
        ).status_code
        == 200
    )


def test_logout_revokes_tokens(client, store):
    tenant, _product, customer, _admin = store
    headers = auth_headers(customer, tenant_id=tenant.slug)
    assert client.get("/api/v1/store/account/me", headers=headers).status_code == 200
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert client.get("/api/v1/store/account/me", headers=headers).status_code == 401


def test_brands_and_pickup_locations(client, store):
    tenant, _product, _customer, admin = store
    admin_headers = auth_headers(admin, tenant_id=tenant.slug)
    created = client.post(
        "/api/v1/brands/", headers=admin_headers, json={"name": "Local Brand"}
    )
    assert created.status_code == 201
    assert client.get("/api/v1/brands/", headers=admin_headers).status_code == 200

    from bopis_svc.bopis_service import BopisService

    BopisService().create_location(
        tenant_id=tenant.id, code="main", name="Main", address={"text": "Center"}
    )
    locations = client.get(
        "/api/v1/store/pickup-locations", headers=tenant_headers(tenant.slug)
    )
    assert locations.status_code == 200
    assert locations.get_json()["locations"]


def test_anonymous_order_payload_has_no_pii(client, store):
    tenant, product, _customer, _admin = store
    from order_svc.cart_service import CartService
    from order_svc.checkout_service import CheckoutService

    cart = CartService().get_or_create_cart(tenant_id=tenant.id)
    CartService().add_item(cart=cart, product_id=product.id, quantity=1)
    order = CheckoutService().checkout(
        cart=cart,
        customer_email="private@flow.com",
        shipping_address={"city": "Ramallah"},
    )
    response = client.get(
        f"/api/v1/store/orders/{order.public_id}", headers=tenant_headers(tenant.slug)
    )
    assert response.status_code == 200
    payload = response.get_json()["order"]
    assert "customer_email" not in payload
    assert "shipping_address" not in payload
