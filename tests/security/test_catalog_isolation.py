"""Catalog tenant isolation (wave 2 #18 extension)."""

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

    list_a = products.list_for_tenant(t1.id)
    list_b = products.list_for_tenant(t2.id)

    assert len(list_a) == 1
    assert len(list_b) == 1
    assert list_a[0].name == "Widget A"
    assert list_b[0].name == "Widget B"
