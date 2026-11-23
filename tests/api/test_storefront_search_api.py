"""GET /api/v1/store/search — text search + filters, JSON payload."""

from __future__ import annotations

from support.http import tenant_headers

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


def _seed():
    tenant = TenantService().create_tenant(
        name="API Search", slug="api-search", email="a@api.test"
    )
    ProductService().create(
        tenant_id=tenant.id,
        name="Blender",
        slug="blender",
        price="199.00",
        is_published=True,
        is_featured=True,
    )
    ProductService().create(
        tenant_id=tenant.id,
        name="Salad Basket",
        slug="basket",
        price="39.00",
        is_published=True,
    )
    return tenant


def test_search_api_returns_matching_products(client, app) -> None:
    tenant = _seed()
    resp = client.get(
        "/api/v1/store/search?q=blender", headers=tenant_headers(tenant.slug)
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 1
    assert data["products"][0]["name"] == "Blender"
    assert data["products"][0]["is_featured"] is True
    assert data["pagination"]["page"] == 1


def test_search_api_no_match(client, app) -> None:
    tenant = _seed()
    resp = client.get(
        "/api/v1/store/search?q=nothing", headers=tenant_headers(tenant.slug)
    )
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 0


def test_search_api_category_filter(client, app) -> None:
    tenant = _seed()
    cat = CategoryService().create(tenant_id=tenant.id, name="Kitchen", slug="kitchen")
    ProductService().create(
        tenant_id=tenant.id,
        name="Wok",
        slug="wok",
        price="79.00",
        category_id=cat.id,
        is_published=True,
    )
    resp = client.get(
        "/api/v1/store/search?category=kitchen",
        headers=tenant_headers(tenant.slug),
    )
    assert resp.status_code == 200
    names = [p["name"] for p in resp.get_json()["products"]]
    assert "Wok" in names and "Salad Basket" not in names


def test_search_api_unknown_category_404(client, app) -> None:
    tenant = _seed()
    resp = client.get(
        "/api/v1/store/search?category=nope",
        headers=tenant_headers(tenant.slug),
    )
    assert resp.status_code == 404
