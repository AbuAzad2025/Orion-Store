"""Product/category translation CRUD and merge (wave 7 #60)."""

from __future__ import annotations

from i18n.category_translation import CategoryTranslation
from i18n.product_translation import ProductTranslation
from i18n_svc.i18n_service import I18nService

from catalog.category import Category
from catalog.product import Product
from core.caching import invalidate_tenant_catalog
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class TranslationService:
    def __init__(self) -> None:
        self._i18n = I18nService()

    def list_product_translations(
        self, tenant_id: int, product_id: int
    ) -> list[ProductTranslation]:
        return (
            ProductTranslation.query.filter_by(
                tenant_id=tenant_id, product_id=product_id
            )
            .order_by(ProductTranslation.locale)
            .all()
        )

    def upsert_product_translation(
        self,
        *,
        tenant_id: int,
        product: Product,
        locale: str,
        name: str,
        description: str | None = None,
        meta_title: str | None = None,
        meta_description: str | None = None,
    ) -> ProductTranslation:
        self._i18n.get_locale(locale)
        row = ProductTranslation.query.filter_by(
            tenant_id=tenant_id, product_id=product.id, locale=locale
        ).first()
        if not row:
            row = ProductTranslation(
                tenant_id=tenant_id,
                product_id=product.id,
                locale=locale,
                name=name.strip(),
            )
            db.session.add(row)
        row.name = name.strip()
        row.description = description
        row.meta_title = meta_title
        row.meta_description = meta_description
        db.session.commit()
        invalidate_tenant_catalog(tenant_id)
        return row

    def upsert_category_translation(
        self,
        *,
        tenant_id: int,
        category: Category,
        locale: str,
        name: str,
        description: str | None = None,
        slug: str | None = None,
    ) -> CategoryTranslation:
        self._i18n.get_locale(locale)
        if (
            slug
            and Category.query.filter_by(
                tenant_id=tenant_id, slug=slug, deleted_at=None
            ).first()
        ):
            existing = Category.query.filter_by(
                tenant_id=tenant_id, slug=slug, deleted_at=None
            ).first()
            if existing and existing.id != category.id:
                raise ValidationError("Category slug already exists.")
        row = CategoryTranslation.query.filter_by(
            tenant_id=tenant_id, category_id=category.id, locale=locale
        ).first()
        if not row:
            row = CategoryTranslation(
                tenant_id=tenant_id,
                category_id=category.id,
                locale=locale,
                name=name.strip(),
            )
            db.session.add(row)
        row.name = name.strip()
        row.description = description
        row.slug = slug
        db.session.commit()
        invalidate_tenant_catalog(tenant_id)
        return row

    def merge_product(self, product: Product, locale: str) -> dict:
        data = product.to_dict()
        trans = ProductTranslation.query.filter_by(
            tenant_id=product.tenant_id, product_id=product.id, locale=locale
        ).first()
        if not trans:
            return {**data, "locale": locale}
        data.update(
            {
                "locale": locale,
                "name": trans.name,
                "description": trans.description or product.description,
                "meta_title": trans.meta_title,
                "meta_description": trans.meta_description,
            }
        )
        return data

    def merge_category(self, category: Category, locale: str) -> dict:
        data = category.to_dict()
        trans = CategoryTranslation.query.filter_by(
            tenant_id=category.tenant_id,
            category_id=category.id,
            locale=locale,
        ).first()
        if not trans:
            return {**data, "locale": locale}
        data.update(
            {
                "locale": locale,
                "name": trans.name,
                "description": trans.description or category.description,
                "slug": trans.slug or category.slug,
            }
        )
        return data

    def get_category_by_localized_slug(
        self, tenant_id: int, slug: str, locale: str
    ) -> Category:
        category = Category.query.filter_by(
            tenant_id=tenant_id, slug=slug, deleted_at=None
        ).first()
        if category:
            return category
        if locale == "ar":
            raise NotFoundError("Category not found.")
        trans = CategoryTranslation.query.filter_by(
            tenant_id=tenant_id, locale=locale, slug=slug
        ).first()
        if not trans:
            raise NotFoundError("Category not found.")
        category = Category.query.filter_by(
            id=trans.category_id, tenant_id=tenant_id, deleted_at=None
        ).first()
        if not category:
            raise NotFoundError("Category not found.")
        return category
