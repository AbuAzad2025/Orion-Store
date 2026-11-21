"""Tenant isolation — negative checks against cross-tenant access (P0)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from support.http import auth_headers

from auth.auth_service import AuthService
from catalog_svc.product_service import ProductService
from core.exceptions import NotFoundError
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


def _seed_tenants(app):
    """Return plain values so no expired ORM object leaks between contexts."""
    tenants = TenantService()
    auth = AuthService()
    products = ProductService()
    with app.app_context():
        t1 = tenants.create_tenant(name="Store A", slug="store-a", email="a@test.com")
        t2 = tenants.create_tenant(name="Store B", slug="store-b", email="b@test.com")
        admin_a = auth.register_tenant_user(
            tenant_id=t1.id,
            email="admin@a.com",
            password="password123",
            is_admin=True,
        )
        auth.register_tenant_user(
            tenant_id=t2.id,
            email="admin@b.com",
            password="password123",
            is_admin=True,
        )
        product_b = products.create(
            tenant_id=t2.id, name="Widget B", slug="widget-b", price="20.00"
        )
        return SimpleNamespace(
            t1_id=t1.id,
            t1_slug=t1.slug,
            t2_id=t2.id,
            admin_a_id=str(admin_a.public_id),
            product_b_public_id=str(product_b.public_id),
            product_b_name=product_b.name,
        )


def test_tenant_a_cannot_see_tenant_b_users(app):
    tenants = TenantService()
    auth = AuthService()

    t1 = tenants.create_tenant(name="Store A", slug="store-a", email="a@test.com")
    t2 = tenants.create_tenant(name="Store B", slug="store-b", email="b@test.com")
    auth.register_tenant_user(
        tenant_id=t1.id, email="admin@a.com", password="password123"
    )
    auth.register_tenant_user(
        tenant_id=t2.id, email="admin@b.com", password="password123"
    )

    users_a = tenants.list_users_for_tenant(t1.id)
    users_b = tenants.list_users_for_tenant(t2.id)

    assert len(users_a) == 1
    assert len(users_b) == 1
    assert all(u.tenant_id == t1.id for u in users_a)
    assert all(u.tenant_id == t2.id for u in users_b)


def test_service_rejects_cross_tenant_product_lookup(app):
    data = _seed_tenants(app)
    with app.app_context(), pytest.raises(NotFoundError):
        ProductService().get_by_public_id(data.t1_id, data.product_b_public_id)


def test_tenant_a_cannot_read_tenant_b_product_over_http(app, client):
    data = _seed_tenants(app)
    with app.app_context():
        headers = auth_headers(data.admin_a_id, tenant_id=data.t1_slug)

    response = client.get(
        f"/api/v1/products/{data.product_b_public_id}", headers=headers
    )
    assert response.status_code in (403, 404)


def test_tenant_a_cannot_update_tenant_b_product_over_http(app, client):
    data = _seed_tenants(app)
    with app.app_context():
        headers = auth_headers(data.admin_a_id, tenant_id=data.t1_slug)

    response = client.put(
        f"/api/v1/products/{data.product_b_public_id}",
        headers=headers,
        json={"name": "Hacked by tenant A"},
    )
    assert response.status_code in (403, 404)

    with app.app_context():
        from catalog.product import Product

        db.session.expire_all()
        product = (
            db.session.query(Product)
            .filter_by(public_id=uuid.UUID(data.product_b_public_id))
            .first()
        )
        assert product is not None
        assert product.name == data.product_b_name


def test_tenant_a_cannot_delete_tenant_b_product_over_http(app, client):
    data = _seed_tenants(app)
    with app.app_context():
        headers = auth_headers(data.admin_a_id, tenant_id=data.t1_slug)

    response = client.delete(
        f"/api/v1/products/{data.product_b_public_id}", headers=headers
    )
    assert response.status_code in (403, 404)


def test_superuser_has_no_tenant_id(app):
    auth = AuthService()
    admin = auth.register_super_admin(email="owner@azadexa.com", password="password123")
    assert admin.is_superuser is True
    assert admin.tenant_id is None
    assert admin.is_customer is False
