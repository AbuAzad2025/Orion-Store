"""Bundle commerce: advertised price, per-order cap and tenant scoping."""

from __future__ import annotations

from decimal import Decimal

from support.http import tenant_headers

from bundle.bundle import BundleItem, ProductBundle
from catalog_svc.product_service import ProductService
from orion.extensions import db
from tenant.tenant import Tenant
from tenant_svc.tenant_service import TenantService


def _make_bundle(app, tenant, *, price="12.00", max_per_order=None, published=True):
    with app.app_context():
        row = db.session.get(Tenant, tenant.id)
        row.phone = "+970501234567"
        bundle = ProductBundle(
            tenant_id=tenant.id,
            name="Combo",
            slug=f"combo-{tenant.id}",
            bundle_price=Decimal(price),
            is_published=published,
            max_per_order=max_per_order,
        )
        db.session.add(bundle)
        db.session.commit()
        product = ProductService().create(
            tenant_id=tenant.id,
            name="Combo item",
            slug=f"combo-item-{tenant.id}",
            price="10.00",
            quantity=10,
            is_published=True,
        )
        db.session.add(
            BundleItem(
                tenant_id=tenant.id,
                bundle_id=bundle.id,
                product_id=product.id,
                quantity=2,
                discount_percent=Decimal("0"),
            )
        )
        db.session.commit()
        return bundle.id


def _cart(client, headers):
    return client.post("/api/v1/store/cart", headers=headers).get_json()["cart"][
        "cart_token"
    ]


def test_bundle_cart_uses_advertised_price(client, app):
    tenant = TenantService().create_tenant(
        name="BC", slug="bc-store", email="bc@test.com"
    )
    bundle_id = _make_bundle(app, tenant)
    headers = tenant_headers(tenant.slug)
    token = _cart(client, headers)
    added = client.post(
        f"/api/v1/store/cart/{token}/bundle",
        headers=headers,
        json={"bundle_id": bundle_id},
    )
    assert added.status_code == 201, added.get_data(as_text=True)
    assert added.get_json()["item"]["unit_price"] == "12.00"
    message = client.post(
        f"/api/v1/store/cart/{token}/whatsapp-message", headers=headers
    ).get_json()["message"]
    assert "12.00 = 12.00" in message
    order = client.post(f"/api/v1/store/cart/{token}/whatsapp-order", headers=headers)
    assert order.status_code == 201, order.get_data(as_text=True)
    with app.app_context():
        from order.order import OrderItem

        row = OrderItem.query.filter_by(tenant_id=tenant.id).one()
        assert Decimal(str(row.unit_price)) == Decimal("12.00")
        assert row.product_id is None


def test_bundle_max_per_order(client, app):
    tenant = TenantService().create_tenant(
        name="BCL", slug="bcl-store", email="bcl@test.com"
    )
    bundle_id = _make_bundle(app, tenant, max_per_order=2)
    headers = tenant_headers(tenant.slug)
    token = _cart(client, headers)
    url = f"/api/v1/store/cart/{token}/bundle"
    added = client.post(
        url, headers=headers, json={"bundle_id": bundle_id, "quantity": 2}
    )
    assert added.status_code == 201, added.get_data(as_text=True)
    denied = client.post(
        url, headers=headers, json={"bundle_id": bundle_id, "quantity": 1}
    )
    assert denied.status_code == 400
    items = client.get(f"/api/v1/store/cart/{token}", headers=headers).get_json()[
        "items"
    ]
    assert items[0]["quantity"] == 2
    assert items[0]["total_price"] == "24.00"


def test_bundle_add_is_tenant_scoped_and_published_only(client, app):
    tenant_a = TenantService().create_tenant(
        name="BA", slug="ba-store", email="ba@test.com"
    )
    tenant_b = TenantService().create_tenant(
        name="BB", slug="bb-store", email="bb@test.com"
    )
    other_bundle = _make_bundle(app, tenant_b)
    draft = _make_bundle(app, tenant_a, published=False)
    headers = tenant_headers(tenant_a.slug)
    token = _cart(client, headers)
    url = f"/api/v1/store/cart/{token}/bundle"
    assert (
        client.post(url, headers=headers, json={"bundle_id": other_bundle}).status_code
        == 404
    )
    assert (
        client.post(url, headers=headers, json={"bundle_id": draft}).status_code == 404
    )
    assert (
        client.get(f"/api/v1/store/cart/{token}", headers=headers).get_json()["items"]
        == []
    )
