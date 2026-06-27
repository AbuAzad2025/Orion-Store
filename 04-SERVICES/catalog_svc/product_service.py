"""Product service — tenant-scoped CRUD (wave 2 #23)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from catalog.product import Product
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class ProductService:
    def list_for_tenant(self, tenant_id: int) -> list[Product]:
        return self.query_for_tenant(tenant_id).all()

    def query_for_tenant(self, tenant_id: int):
        return Product.query.filter_by(tenant_id=tenant_id, deleted_at=None).order_by(
            Product.created_at.desc()
        )

    def list_published(self, tenant_id: int) -> list[Product]:
        return self.query_published(tenant_id).all()

    def query_published(self, tenant_id: int):
        return Product.query.filter_by(
            tenant_id=tenant_id, deleted_at=None, is_published=True
        ).order_by(Product.created_at.desc())

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
    ) -> Product:
        if Product.query.filter_by(tenant_id=tenant_id, slug=slug).first():
            raise ValidationError("Product slug already exists.")
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
        )
        db.session.add(product)
        db.session.commit()
        return product

    def update(self, product: Product, **fields) -> Product:
        if "slug" in fields and fields["slug"] != product.slug:
            clash = Product.query.filter_by(
                tenant_id=product.tenant_id, slug=fields["slug"]
            ).first()
            if clash and clash.id != product.id:
                raise ValidationError("Product slug already exists.")
        for key, value in fields.items():
            if key == "price" and value is not None:
                value = Decimal(str(value))
            if hasattr(product, key) and value is not None:
                setattr(product, key, value)
        product.version += 1
        db.session.commit()
        return product

    def soft_delete(self, product: Product) -> None:
        from core.utils import utc_now

        product.deleted_at = utc_now()
        product.is_active = False
        db.session.commit()
