"""Product service — tenant-scoped CRUD (wave 2 #23)."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import load_only

from catalog.product import Product
from core.caching import invalidate_tenant_catalog
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


def _escape_like_wildcard(term: str) -> str:
    """Escape LIKE wildcards so a search term can never match more than itself."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_PUBLISHED_COLUMNS = load_only(
    Product.id,
    Product.public_id,
    Product.tenant_id,
    Product.name,
    Product.slug,
    Product.sku,
    Product.image_url,
    Product.short_description,
    Product.description,
    Product.is_featured,
    Product.compare_at_price,
    Product.price,
    Product.quantity,
    Product.is_published,
    Product.category_id,
    Product.brand_id,
)


def _sync_stock_to_warehouse(product: Product) -> None:
    """Keep the per-tenant warehouse aligned with the saleable product stock."""
    try:
        from oms_svc.oms_service import OmsService

        OmsService().sync_product_to_warehouse(
            tenant_id=product.tenant_id, product_id=product.id
        )
    except Exception as exc:  # inventory must never block catalog edits
        logging.getLogger(__name__).warning(
            "warehouse sync failed for product %s: %s", product.id, exc
        )


def _validate_category_brand(tenant_id: int, fields: dict) -> None:
    """Reject category/brand ids belonging to another tenant."""
    from catalog.brand import Brand
    from catalog.category import Category

    category_id = fields.get("category_id")
    if (
        category_id is not None
        and not Category.query.filter_by(id=category_id, tenant_id=tenant_id).first()
    ):
        raise ValidationError("Category not found.")
    brand_id = fields.get("brand_id")
    if (
        brand_id is not None
        and not Brand.query.filter_by(id=brand_id, tenant_id=tenant_id).first()
    ):
        raise ValidationError("Brand not found.")


class ProductService:
    def list_for_tenant(self, tenant_id: int) -> list[Product]:
        return self.query_for_tenant(tenant_id).all()

    def query_for_tenant(self, tenant_id: int):
        return Product.query.filter_by(tenant_id=tenant_id, deleted_at=None).order_by(
            Product.created_at.desc()
        )

    def list_published(self, tenant_id: int) -> list[Product]:
        return self.query_published(tenant_id).all()

    def query_published(
        self,
        tenant_id: int,
        *,
        category_id: int | None = None,
        featured: bool | None = None,
        price_min: Decimal | str | None = None,
        price_max: Decimal | str | None = None,
        sort: str | None = None,
    ):
        """Published products with optional catalog filters (tenant-scoped).

        Default order stays newest-first (legacy behavior); ``sort`` accepts
        ``"featured"``, ``"price_asc"`` or ``"price_desc"``.
        """
        q = Product.query.filter_by(
            tenant_id=tenant_id, deleted_at=None, is_published=True
        ).options(_PUBLISHED_COLUMNS)
        if category_id is not None:
            q = q.filter_by(category_id=category_id)
        if featured is not None:
            q = q.filter_by(is_featured=featured)
        if price_min is not None:
            q = q.filter(Product.price >= Decimal(str(price_min)))
        if price_max is not None:
            q = q.filter(Product.price <= Decimal(str(price_max)))
        if sort == "price_asc":
            q = q.order_by(Product.price.asc(), Product.created_at.desc())
        elif sort == "price_desc":
            q = q.order_by(Product.price.desc(), Product.created_at.desc())
        elif sort == "featured":
            q = q.order_by(Product.is_featured.desc(), Product.created_at.desc())
        else:
            q = q.order_by(Product.created_at.desc())
        return q

    SORT_OPTIONS = ("default", "price_asc", "price_desc")

    def query_search_published(
        self,
        tenant_id: int,
        query: str | None = None,
        *,
        category_id: int | None = None,
        featured: bool | None = None,
        price_min: Decimal | str | None = None,
        price_max: Decimal | str | None = None,
        sort: str = "default",
    ):
        """Published products matching a text search + filters, deterministically sorted.

        Search default surfaces featured products first, then newest.
        """
        q = self.query_published(
            tenant_id,
            category_id=category_id,
            featured=featured,
            price_min=price_min,
            price_max=price_max,
            sort="featured" if sort in ("default", "featured") else sort,
        )
        term = (query or "").strip()
        if term:
            from i18n.product_translation import ProductTranslation

            needle = _escape_like_wildcard(term)
            pattern = f"%{needle}%"
            translated_ids = db.session.query(ProductTranslation.product_id).filter(
                ProductTranslation.tenant_id == tenant_id,
                or_(
                    ProductTranslation.name.ilike(pattern, escape="\\"),
                    ProductTranslation.description.ilike(pattern, escape="\\"),
                ),
            )
            q = q.filter(
                or_(
                    Product.name.ilike(pattern, escape="\\"),
                    Product.short_description.ilike(pattern, escape="\\"),
                    Product.description.ilike(pattern, escape="\\"),
                    Product.id.in_(translated_ids),
                )
            )
        return q

    def search_published(
        self,
        tenant_id: int,
        query: str | None = None,
        *,
        category_id: int | None = None,
        featured: bool | None = None,
        price_min: Decimal | str | None = None,
        price_max: Decimal | str | None = None,
        sort: str = "default",
    ) -> list[Product]:
        return self.query_search_published(
            tenant_id,
            query,
            category_id=category_id,
            featured=featured,
            price_min=price_min,
            price_max=price_max,
            sort=sort,
        ).all()

    def get_by_slug(self, tenant_id: int, slug: str) -> Product:
        product = Product.query.filter_by(
            tenant_id=tenant_id, slug=slug, deleted_at=None, is_published=True
        ).first()
        if not product:
            raise NotFoundError("Product not found.")
        return product

    def get_by_public_id(self, tenant_id: int, public_id: str) -> Product:
        try:
            pid = uuid.UUID(public_id)
        except ValueError as exc:
            raise NotFoundError("Product not found.") from exc
        product = Product.query.filter_by(
            public_id=pid, tenant_id=tenant_id, deleted_at=None
        ).first()
        if not product:
            raise NotFoundError("Product not found.")
        return product

    def create(
        self,
        *,
        tenant_id: int,
        name: str,
        slug: str,
        price: Decimal | str,
        sku: str | None = None,
        quantity: int = 0,
        category_id: int | None = None,
        brand_id: int | None = None,
        is_published: bool = False,
        is_featured: bool = False,
        image_url: str | None = None,
        short_description: str | None = None,
        description: str | None = None,
        compare_at_price: str | Decimal | None = None,
    ) -> Product:
        if Product.query.filter_by(tenant_id=tenant_id, slug=slug).first():
            raise ValidationError("Product slug already exists.")
        _validate_category_brand(
            tenant_id, {"category_id": category_id, "brand_id": brand_id}
        )
        product = Product(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            sku=sku,
            price=Decimal(str(price)),
            quantity=quantity,
            category_id=category_id,
            brand_id=brand_id,
            is_published=is_published,
            is_featured=is_featured,
            image_url=image_url,
            short_description=short_description,
            description=description,
            compare_at_price=(
                Decimal(str(compare_at_price)) if compare_at_price is not None else None
            ),
        )
        db.session.add(product)
        db.session.commit()
        _sync_stock_to_warehouse(product)
        invalidate_tenant_catalog(tenant_id)
        return product

    def update(self, product: Product, **fields) -> Product:
        was_out_of_stock = product.quantity == 0
        if "slug" in fields and fields["slug"] != product.slug:
            clash = Product.query.filter_by(
                tenant_id=product.tenant_id, slug=fields["slug"]
            ).first()
            if clash and clash.id != product.id:
                raise ValidationError("Product slug already exists.")
        _validate_category_brand(
            product.tenant_id,
            {
                "category_id": fields.get("category_id"),
                "brand_id": fields.get("brand_id"),
            },
        )
        for key, value in fields.items():
            if key == "price" and value is not None:
                value = Decimal(str(value))
            if hasattr(product, key) and value is not None:
                setattr(product, key, value)
        product.version += 1
        db.session.commit()
        if "quantity" in fields:
            _sync_stock_to_warehouse(product)
            if was_out_of_stock and product.quantity > 0:
                try:
                    from stock_notification_svc.stock_notification_service import (
                        StockNotificationService,
                    )

                    StockNotificationService().notify_for_product(
                        tenant_id=product.tenant_id, product_id=product.id
                    )
                except Exception as exc:  # notifications must not block catalog edits
                    logging.getLogger(__name__).warning(
                        "restock notification failed for product %s: %s",
                        product.id,
                        exc,
                    )
        invalidate_tenant_catalog(product.tenant_id)
        return product

    def soft_delete(self, product: Product) -> None:
        from core.utils import utc_now

        product.deleted_at = utc_now()
        product.is_active = False
        db.session.commit()
        invalidate_tenant_catalog(product.tenant_id)
