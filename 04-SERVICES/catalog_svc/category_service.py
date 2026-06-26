"""Category service — tenant-scoped listing (wave 2 #23)."""

from __future__ import annotations

from catalog.category import Category
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class CategoryService:
    def list_for_tenant(self, tenant_id: int) -> list[Category]:
        return (
            Category.query.filter_by(tenant_id=tenant_id, deleted_at=None)
            .order_by(Category.sort_order, Category.name)
            .all()
        )

    def create(
        self,
        *,
        tenant_id: int,
        name: str,
        slug: str,
        parent_id: int | None = None,
    ) -> Category:
        if Category.query.filter_by(tenant_id=tenant_id, slug=slug).first():
            raise ValidationError("Category slug already exists.")
        level = 0
        path = slug
        if parent_id:
            parent = Category.query.filter_by(
                id=parent_id, tenant_id=tenant_id, deleted_at=None
            ).first()
            if not parent:
                raise NotFoundError("Parent category not found.")
            level = parent.level + 1
            path = f"{parent.path}/{slug}" if parent.path else slug
        category = Category(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            parent_id=parent_id,
            level=level,
            path=path,
        )
        db.session.add(category)
        db.session.commit()
        return category
