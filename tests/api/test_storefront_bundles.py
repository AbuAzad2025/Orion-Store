"""Published product bundles are the only ones exposed to storefront visitors."""

from __future__ import annotations

from decimal import Decimal

from support.http import tenant_headers

from auth.auth_service import AuthService
from bundle.bundle import BundleItem, ProductBundle
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService


def test_storefront_lists_only_published_bundles(client, app):
    tenant = TenantService().create_tenant(
        name="Bundle Store", slug="bundle-store", email="b@test.com"
    )
    product = ProductService().create(
        tenant_id=tenant.id,
        name="Bundle Item",
        slug="bundle-item",
        price="10.00",
        quantity=5,
        is_published=True,
    )
    with app.app_context():
        published = ProductBundle(
            tenant_id=tenant.id,
            name="Published set",
            slug="published-set",
            bundle_price=Decimal("18.00"),
            is_published=True,
        )
        hidden = ProductBundle(
            tenant_id=tenant.id,
            name="Draft set",
            slug="draft-set",
            bundle_price=Decimal("5.00"),
            is_published=False,
        )
        from orion.extensions import db

        db.session.add_all([published, hidden])
        db.session.commit()
        db.session.add(
            BundleItem(
                tenant_id=tenant.id,
                bundle_id=published.id,
                product_id=product.id,
                quantity=2,
                discount_percent=Decimal("10"),
            )
        )
        db.session.commit()

    headers = tenant_headers(tenant.slug)
    resp = client.get("/api/v1/store/bundles", headers=headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    bundles = resp.get_json()["bundles"]
    assert [b["slug"] for b in bundles] == ["published-set"]
    bundle = bundles[0]
    assert len(bundle["items"]) == 1
    assert bundle["items"][0]["public_id"] == product.public_id
    assert bundle["original_total"] == "18.00"
    assert bundle["savings"] == "0.00"

    detail = client.get("/api/v1/store/bundles/draft-set", headers=headers)
    assert detail.status_code == 404
