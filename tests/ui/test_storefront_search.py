"""Storefront search page + catalog filters render and behave correctly."""

from __future__ import annotations

import re

from support.http import tenant_headers

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


def _seed():
    from feature_flag_svc.feature_flag_service import FeatureFlagService

    tenant = TenantService().create_tenant(
        name="Search Store", slug="search-store", email="s@search.test"
    )
    FeatureFlagService().set_tenant_override(
        tenant_id=tenant.id, code="multi_language", value=True
    )
    cat_a = CategoryService().create(
        tenant_id=tenant.id, name="Kitchen", slug="kitchen"
    )
    cat_b = CategoryService().create(tenant_id=tenant.id, name="Bath", slug="bath")
    return tenant, cat_a, cat_b


def _product(tenant, name, slug, price="9.99", category=None, featured=False):
    return ProductService().create(
        tenant_id=tenant.id,
        name=name,
        slug=slug,
        price=price,
        category_id=category.id if category else None,
        is_published=True,
        is_featured=featured,
    )


def test_header_search_box_present(client, app) -> None:
    tenant, _, _ = _seed()
    resp = client.get("/", headers=tenant_headers(tenant.slug))
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert 'class="orion-search-input"' in text
    assert "/search" in text


def test_search_page_renders_results_with_filters(client, app) -> None:
    tenant, _, _ = _seed()
    _product(tenant, "Coffee Maker", "coffee-maker", "899.00", featured=True)
    _product(tenant, "Coffee Grinder", "coffee-grinder", "199.00")
    resp = client.get("/search?q=coffee", headers=tenant_headers(tenant.slug))
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "نتائج البحث" in text  # search_results_title (ar)
    assert "Coffee Maker" in text and "Coffee Grinder" in text
    assert 'class="orion-filters"' in text
    assert "مميز" in text  # featured checkbox


def test_search_page_english_locale(client, app) -> None:
    tenant, _, _ = _seed()
    _product(tenant, "Coffee Maker", "coffee-maker")
    resp = client.get("/search?q=coffee&locale=en", headers=tenant_headers(tenant.slug))
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Search results" in text
    assert "Search products" in text or "Filters" in text


def test_search_no_results(client, app) -> None:
    tenant, _, _ = _seed()
    _product(tenant, "Coffee Maker", "coffee-maker")
    resp = client.get("/search?q=zzz-nothing", headers=tenant_headers(tenant.slug))
    assert resp.status_code == 200
    assert "لا توجد منتجات مطابقة" in resp.get_data(as_text=True)


def test_catalog_filters_bar_renders(client, app) -> None:
    tenant, cat_a, cat_b = _seed()
    _product(tenant, "Mixer", "mixer", category=cat_a)
    resp = client.get("/", headers=tenant_headers(tenant.slug))
    text = resp.get_data(as_text=True)
    assert 'class="orion-filters"' in text
    assert "Kitchen" in text and "Bath" in text


def test_catalog_category_filter_narrows_products(client, app) -> None:
    tenant, cat_a, cat_b = _seed()
    _product(tenant, "Mixer", "mixer", category=cat_a)
    _product(tenant, "Toilet Brush", "brush", category=cat_b)
    resp = client.get("/?category=bath", headers=tenant_headers(tenant.slug))
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Toilet Brush" in text
    assert "Mixer" not in text


def test_search_price_filter(client, app) -> None:
    tenant, _, _ = _seed()
    _product(tenant, "Small thing", "small-thing", "30.00")
    _product(tenant, "Big thing", "big-thing", "300.00")
    resp = client.get(
        "/search?price_min=50&price_max=500", headers=tenant_headers(tenant.slug)
    )
    text = resp.get_data(as_text=True)
    assert "Big thing" in text
    assert "Small thing" not in text


def test_search_featured_filter(client, app) -> None:
    tenant, _, _ = _seed()
    _product(tenant, "Hot Deal", "hot", featured=True)
    _product(tenant, "Regular Deal", "regular")
    resp = client.get("/search?featured=1", headers=tenant_headers(tenant.slug))
    text = resp.get_data(as_text=True)
    assert "Hot Deal" in text
    assert "Regular Deal" not in text


def test_language_switch_preserves_search_query(client, app) -> None:
    tenant, _, _ = _seed()
    _product(tenant, "Coffee Maker", "coffee-maker")
    resp = client.get("/search?q=coffee", headers=tenant_headers(tenant.slug))
    text = resp.get_data(as_text=True)
    en_link = re.search(r'href="([^"]*locale=en[^"]*)"', text)
    assert en_link and "q=coffee" in en_link.group(1)


def test_search_sort_price_desc(client, app) -> None:
    tenant, _, _ = _seed()
    _product(tenant, "Small thing", "small-thing", "30.00")
    _product(tenant, "Big thing", "big-thing", "300.00")
    resp = client.get("/search?sort=price_desc", headers=tenant_headers(tenant.slug))
    text = resp.get_data(as_text=True)
    assert text.index("Big thing") < text.index("Small thing")
