"""ProductService search/filter behavior — text search + filters + sort."""

from __future__ import annotations

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


def _seed(name="Search", slug="search-tenant"):
    tenant = TenantService().create_tenant(
        name=name, slug=slug, email="search@test.com"
    )
    products = ProductService()
    category = CategoryService().create(
        tenant_id=tenant.id, name="Electronics", slug="electronics"
    )
    other = CategoryService().create(tenant_id=tenant.id, name="Books", slug="books")
    return tenant, products, category, other


def _product(products, tenant, name, price, category=None, featured=False):
    return products.create(
        tenant_id=tenant.id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        price=price,
        category_id=category.id if category else None,
        is_published=True,
        is_featured=featured,
    )


def test_search_by_name_case_insensitive(app) -> None:
    tenant, products, _, _ = _seed()
    _product(products, tenant, "iPhone 15 Pro", "999.00")
    _product(products, tenant, "winter jacket", "120.00")
    assert [p.name for p in products.search_published(tenant.id, "iphone")] == [
        "iPhone 15 Pro"
    ]
    assert [p.name for p in products.search_published(tenant.id, "IPHONE 15 PRO")] == [
        "iPhone 15 Pro"
    ]
    assert products.search_published(tenant.id, "no-such-thing") == []
    assert len(products.search_published(tenant.id)) == 2


def test_search_by_description(app) -> None:
    tenant, products, _, _ = _seed()
    products.create(
        tenant_id=tenant.id,
        name="Portable Fan",
        slug="fan",
        price="50.00",
        is_published=True,
        short_description="Cools your desk during summer",
    )
    assert [p.name for p in products.search_published(tenant.id, "summer")] == [
        "Portable Fan"
    ]


def test_search_matches_translated_name(app) -> None:
    from i18n.product_translation import ProductTranslation

    tenant, products, _, _ = _seed()
    product = _product(products, tenant, "هاتف ذكي", "399.00")
    db.session.add(
        ProductTranslation(
            tenant_id=tenant.id,
            product_id=product.id,
            locale="en",
            name="Smart Phone",
            description="A fast mobile phone",
        )
    )
    db.session.commit()
    assert [p.name for p in products.search_published(tenant.id, "phone")] == [
        "هاتف ذكي"
    ]
    assert [p.name for p in products.search_published(tenant.id, "mobile")] == [
        "هاتف ذكي"
    ]


def test_search_unpublished_not_returned(app) -> None:
    tenant, products, _, _ = _seed()
    products.create(
        tenant_id=tenant.id,
        name="Hidden Thing",
        slug="hidden",
        price="5.00",
        is_published=False,
    )
    assert products.search_published(tenant.id, "hidden") == []


def test_search_category_filter(app) -> None:
    tenant, products, electronics, books = _seed()
    _product(products, tenant, "Headphones", "299.00", category=electronics)
    _product(products, tenant, "Gutenberg Bible", "79.00", category=books)
    results = products.search_published(tenant.id, "", category_id=electronics.id)
    assert [p.name for p in results] == ["Headphones"]


def test_search_featured_filter(app) -> None:
    tenant, products, _, _ = _seed()
    _product(products, tenant, "Hot Deal", "9.99", featured=True)
    _product(products, tenant, "Regular Deal", "4.99")
    assert [
        p.name for p in products.search_published(tenant.id, "", featured=True)
    ] == ["Hot Deal"]
    assert [
        p.name for p in products.search_published(tenant.id, "", featured=False)
    ] == ["Regular Deal"]


def test_search_price_range(app) -> None:
    tenant, products, _, _ = _seed()
    _product(products, tenant, "Small Chair", "50.00")
    _product(products, tenant, "Big Sofa", "250.00")
    results = products.search_published(tenant.id, "", price_min="60", price_max="240")
    assert (
        products.search_published(tenant.id, "", price_min="60")[0].name == "Big Sofa"
    )
    assert [p.name for p in results] == []
    assert len(products.search_published(tenant.id, "", price_max="60")) == 1


def test_search_sort_price_asc_desc(app) -> None:
    tenant, products, _, _ = _seed()
    _product(products, tenant, "SoFa", "250.00")
    _product(products, tenant, "Chair", "50.00")
    _product(products, tenant, "Desk", "120.00")
    asc = [p.name for p in products.search_published(tenant.id, "", sort="price_asc")]
    desc = [p.name for p in products.search_published(tenant.id, "", sort="price_desc")]
    assert asc[0] == "Chair" and asc[-1] == "SoFa"
    assert desc[0] == "SoFa" and desc[-1] == "Chair"


def test_search_default_sort_surfaces_featured(app) -> None:
    tenant, products, _, _ = _seed()
    _product(products, tenant, "Regular", "9.99")
    _product(products, tenant, "Premium", "49.99", featured=True)
    assert [p.name for p in products.search_published(tenant.id, "")][0] == "Premium"
    assert [
        p.name for p in products.search_published(tenant.id, "", featured=True)
    ] == ["Premium"]
