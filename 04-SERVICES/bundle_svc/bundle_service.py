from __future__ import annotations

from decimal import Decimal, InvalidOperation

from bundle.bundle import BundleItem, ProductBundle

from catalog.product import Product
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class BundleService:
    def create_bundle(
        self,
        *,
        tenant_id: int,
        name: str,
        name_en: str | None = None,
        slug: str,
        bundle_price: str | Decimal,
        description: str | None = None,
        image_url: str | None = None,
        max_per_order: int | None = None,
        is_published: bool = False,
    ) -> ProductBundle:
        b = ProductBundle(
            tenant_id=tenant_id,
            name=name,
            name_en=name_en,
            slug=slug,
            description=description,
            image_url=image_url,
            bundle_price=Decimal(str(bundle_price)),
            max_per_order=max_per_order,
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
        self._tenant_bundle(tenant_id=tenant_id, bundle_id=bundle_id)
        self._tenant_product(tenant_id=tenant_id, product_id=product_id)
        item = BundleItem(
            tenant_id=tenant_id,
            bundle_id=bundle_id,
            product_id=product_id,
            quantity=self._valid_quantity(quantity),
            discount_percent=self._valid_discount(discount_percent),
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
            prod = Product.query.filter_by(
                id=item.product_id, tenant_id=bundle.tenant_id
            ).first()
            if prod:
                price = prod.price * (1 - item.discount_percent / Decimal("100"))
                total += price * item.quantity
        return total

    # --- admin item CRUD: tenant-scoped, validation-first -----------------
    def list_items(self, *, tenant_id: int, bundle_id: int) -> list[BundleItem]:
        self._tenant_bundle(tenant_id=tenant_id, bundle_id=bundle_id)
        return (
            BundleItem.query.filter_by(tenant_id=tenant_id, bundle_id=bundle_id)
            .order_by(BundleItem.id)
            .all()
        )

    def update_item(
        self,
        *,
        tenant_id: int,
        bundle_id: int,
        item_id: int,
        quantity: int | str | None = None,
        discount_percent: str | Decimal | None = None,
    ) -> BundleItem:
        item = self._tenant_item(
            tenant_id=tenant_id, bundle_id=bundle_id, item_id=item_id
        )
        if quantity is None and discount_percent is None:
            raise ValidationError("Validation failed.")
        if quantity is not None:
            item.quantity = self._valid_quantity(quantity)
        if discount_percent is not None:
            item.discount_percent = self._valid_discount(discount_percent)
        db.session.commit()
        return item

    def delete_item(self, *, tenant_id: int, bundle_id: int, item_id: int) -> None:
        item = self._tenant_item(
            tenant_id=tenant_id, bundle_id=bundle_id, item_id=item_id
        )
        db.session.delete(item)
        db.session.commit()

    def _tenant_bundle(self, *, tenant_id: int, bundle_id: int) -> ProductBundle:
        bundle = ProductBundle.query.filter_by(
            id=bundle_id, tenant_id=tenant_id
        ).first()
        if not bundle:
            raise NotFoundError("Bundle not found.")
        return bundle

    def _tenant_product(self, *, tenant_id: int, product_id: int) -> Product:
        product = Product.query.filter_by(
            id=product_id, tenant_id=tenant_id, deleted_at=None
        ).first()
        if not product:
            raise NotFoundError("Product not found.")
        return product

    def _tenant_item(
        self, *, tenant_id: int, bundle_id: int, item_id: int
    ) -> BundleItem:
        self._tenant_bundle(tenant_id=tenant_id, bundle_id=bundle_id)
        item = BundleItem.query.filter_by(
            id=item_id, bundle_id=bundle_id, tenant_id=tenant_id
        ).first()
        if not item:
            raise NotFoundError("Bundle item not found.")
        return item

    @staticmethod
    def _valid_quantity(value) -> int:
        if isinstance(value, bool):
            raise ValidationError("Quantity must be at least 1.")
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            raise ValidationError("Quantity must be at least 1.") from None
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        return quantity

    @staticmethod
    def _valid_discount(value) -> Decimal:
        try:
            discount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("Validation failed.") from None
        if not discount.is_finite() or not (Decimal("0") <= discount <= Decimal("100")):
            raise ValidationError("Discount percent must be between 0 and 100.")
        return discount
