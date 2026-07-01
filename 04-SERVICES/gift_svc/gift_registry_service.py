from __future__ import annotations

import uuid

from core.exceptions import NotFoundError
from gift.gift_registry import GiftRegistry, GiftRegistryItem
from orion.extensions import db


class GiftRegistryService:
    def create_registry(self, *, tenant_id: int, customer_email: str, registry_name: str, event_type: str | None = None, event_date: str | None = None, is_public: bool = True) -> GiftRegistry:
        slug = f"{registry_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        r = GiftRegistry(tenant_id=tenant_id, customer_email=customer_email.strip().lower(), registry_name=registry_name, event_type=event_type, event_date=event_date, is_public=is_public, slug=slug)
        db.session.add(r)
        db.session.commit()
        return r

    def add_item(self, *, registry_id: int, product_id: int, quantity: int = 1) -> GiftRegistryItem:
        item = GiftRegistryItem(registry_id=registry_id, product_id=product_id, requested_quantity=quantity)
        db.session.add(item)
        db.session.commit()
        return item

    def get_by_slug(self, slug: str) -> GiftRegistry:
        r = GiftRegistry.query.filter_by(slug=slug, is_public=True).first()
        if not r:
            raise NotFoundError("Registry not found.")
        return r
