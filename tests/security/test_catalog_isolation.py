"""Catalog tenant isolation — cross-tenant reads must be empty (P0)."""

from __future__ import annotations

from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


def test_tenant_a_cannot_see_tenant_b_products(app):
    tenants = TenantService()
    products = ProductService()

    t1 = tenants.create_tenant(name="P Store A", slug="p-store-a", email="pa@test.com")
    t2 = tenants.create_tenant(name="P Store B", slug="p-store-b", email="pb@test.com")

    products.create(tenant_id=t1.id, name="Widget A", slug="widget-a", price="10.00")
    products.create(tenant_id=t2.id, name="Widget B", slug="widget-b", price="20.00")

    with app.app_context():
        list_a = products.query_for_tenant(t1.id).all()
        list_b = products.query_for_tenant(t2.id).all()

    assert [p.name for p in list_a] == ["Widget A"]
    assert [p.name for p in list_b] == ["Widget B"]
    assert not any(p.tenant_id == t2.id for p in list_a)
    assert not any(p.tenant_id == t1.id for p in list_b)


def test_service_create_rejects_unknown_tenant(app):
    products = ProductService()
    with app.app_context():
        try:
            products.create(
                tenant_id=999999, name="Orphan", slug="orphan", price="1.00"
            )
        except Exception:
            return
    raise AssertionError("Creating a product for a non-existent tenant must fail")
