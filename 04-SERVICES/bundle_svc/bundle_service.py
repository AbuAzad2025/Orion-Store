from __future__ import annotations

from decimal import Decimal

from bundle.bundle import BundleItem, ProductBundle

from catalog.product import Product
from core.exceptions import NotFoundError
from orion.extensions import db


class BundleService:
    def create_bundle(
        self,
        *,
        tenant_id: int,
        name: str,
        slug: str,
        bundle_price: str | Decimal,
        description: str | None = None,
        is_published: bool = False,
    ) -> ProductBundle:
        b = ProductBundle(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            bundle_price=Decimal(str(bundle_price)),
            is_published=bool(is_published),
        )
        db.session.add(b)
        db.session.commit()
        return b

    def add_item(
        self,
        *,
        tenant_id: int,
        bundle_id: int,
        product_id: int,
        quantity: int = 1,
        discount_percent: str | Decimal = "0",
    ) -> BundleItem:
        bundle = ProductBundle.query.filter_by(
            id=bundle_id, tenant_id=tenant_id
        ).first()
        if not bundle:
            raise NotFoundError("Bundle not found.")
        item = BundleItem(
            tenant_id=tenant_id,
            bundle_id=bundle_id,
            product_id=product_id,
            quantity=quantity,
            discount_percent=Decimal(str(discount_percent)),
        )
        db.session.add(item)
        db.session.commit()
        return item

    def list_bundles(self, tenant_id: int) -> list[ProductBundle]:
        return ProductBundle.query.filter_by(tenant_id=tenant_id).all()

    def list_published(self, tenant_id: int) -> list[ProductBundle]:
        return (
            ProductBundle.query.filter_by(tenant_id=tenant_id, is_published=True)
            .order_by(ProductBundle.id.desc())
            .all()
        )

    def get_published_by_slug(self, tenant_id: int, slug: str) -> ProductBundle | None:
        return ProductBundle.query.filter_by(
            tenant_id=tenant_id, slug=slug, is_published=True
        ).first()

    def items_for(self, bundle_id: int) -> list[BundleItem]:
        return BundleItem.query.filter_by(bundle_id=bundle_id).all()

    def resolve_bundle_price(self, bundle: ProductBundle) -> Decimal:
        items = BundleItem.query.filter_by(bundle_id=bundle.id).all()
        total = Decimal("0")
        for item in items:
            prod = Product.query.filter_by(id=item.product_id).first()
            if prod:
                price = prod.price * (1 - item.discount_percent / Decimal("100"))
                total += price * item.quantity
        return total
