"""Tenant admins can fully manage products, including images."""

from __future__ import annotations

from support.http import auth_headers

from auth.auth_service import AuthService
from tenant_svc.tenant_service import TenantService


def _store_with_admin(app):
    tenant = TenantService().create_tenant(
        name="Catalog Store", slug="catalog-store", email="catalog@test.com"
    )
    admin = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="catalog-admin@test.com",
        password="password123",
        is_admin=True,
    )
    return tenant, admin


def test_create_and_update_product_with_image(client, app):
    tenant, admin = _store_with_admin(app)
    headers = auth_headers(admin, tenant_id=tenant.slug)

    created = client.post(
        "/api/v1/products/",
        headers=headers,
        json={
            "name": "صورة منتج",
            "slug": "image-product",
            "price": "49.50",
            "quantity": 7,
            "image_url": "https://example.com/product.jpg",
            "short_description": "وصف مختصر",
            "is_featured": True,
            "is_published": True,
        },
    )
    assert created.status_code == 201
    product = created.get_json()["product"]
    assert product["image_url"] == "https://example.com/product.jpg"
    assert product["short_description"] == "وصف مختصر"
    assert product["is_featured"] is True

    updated = client.put(
        f"/api/v1/products/{product['public_id']}",
        headers=headers,
        json={"price": "59.50", "image_url": "/static/product2.jpg"},
    )
    assert updated.status_code == 200
    fetched = client.get(
        f"/api/v1/products/{product['public_id']}", headers=headers
    ).get_json()["product"]
    assert fetched["price"] == "59.50"
    assert fetched["image_url"] == "/static/product2.jpg"


def test_unsafe_image_url_rejected(client, app):
    tenant, admin = _store_with_admin(app)
    headers = auth_headers(admin, tenant_id=tenant.slug)
    response = client.post(
        "/api/v1/products/",
        headers=headers,
        json={
            "name": "XSS",
            "slug": "xss-product",
            "price": "1.00",
            "image_url": "javascript:alert(1)",
        },
    )
    assert response.status_code == 400


def test_customer_cannot_manage_products(client, app):
    tenant = TenantService().create_tenant(
        name="Catalog Store 2", slug="catalog-store-2", email="c2@test.com"
    )
    customer = AuthService().register_tenant_user(
        tenant_id=tenant.id,
        email="catalog-customer@test.com",
        password="password123",
        is_admin=False,
    )
    response = client.post(
        "/api/v1/products/",
        headers=auth_headers(customer, tenant_id=tenant.slug),
        json={"name": "No", "slug": "no", "price": "1.00"},
    )
    assert response.status_code in (401, 403)
