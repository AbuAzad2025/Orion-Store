from __future__ import annotations

import uuid

from gift.gift_registry import GiftRegistry, GiftRegistryItem

from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db


class GiftRegistryService:
    def create_registry(
        self,
        *,
        tenant_id: int,
        customer_email: str,
        registry_name: str,
        event_type: str | None = None,
        event_date: str | None = None,
        is_public: bool = True,
        user_id: int | None = None,
    ) -> GiftRegistry:
        slug = f"{registry_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        r = GiftRegistry(
            tenant_id=tenant_id,
            customer_email=customer_email.strip().lower(),
            user_id=user_id,
            registry_name=registry_name,
            event_type=event_type,
            event_date=event_date,
            is_public=is_public,
            slug=slug,
        )
        db.session.add(r)
        db.session.commit()
        return r

    def add_item(
        self, *, tenant_id: int, registry_id: int, product_id: int, quantity: int = 1
    ) -> GiftRegistryItem:
        from catalog.product import Product

        registry = GiftRegistry.query.filter_by(
            id=registry_id, tenant_id=tenant_id
        ).first()
        product = Product.query.filter_by(id=product_id, tenant_id=tenant_id).first()
        if not registry:
            raise NotFoundError("Registry not found.")
        if not product:
            raise NotFoundError("Product not found.")
        if quantity < 1:
            raise ValidationError("Quantity must be positive.")
        item = GiftRegistryItem(
            tenant_id=tenant_id,
            registry_id=registry_id,
            product_id=product_id,
            requested_quantity=quantity,
        )
        db.session.add(item)
        db.session.commit()
        return item

    def list_items(self, *, registry_id: int) -> list[GiftRegistryItem]:
        """Items for a registry already verified as belonging to the tenant."""
        return (
            GiftRegistryItem.query.filter_by(registry_id=registry_id)
            .order_by(GiftRegistryItem.id.asc())
            .all()
        )

    def get_by_slug(self, slug: str, tenant_id: int) -> GiftRegistry:
        r = GiftRegistry.query.filter_by(
            slug=slug, is_public=True, tenant_id=tenant_id
        ).first()
        if not r:
            raise NotFoundError("Registry not found.")
        return r
