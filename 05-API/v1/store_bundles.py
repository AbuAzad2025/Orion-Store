"""Public storefront bundle endpoints — published bundles only."""

from __future__ import annotations

from decimal import Decimal

from bundle_svc.bundle_service import BundleService
from flask import g, jsonify
from i18n_svc.translation_service import TranslationService

from catalog_svc.product_service import ProductService
from core.exceptions import NotFoundError, OrionError
from core.middleware import require_tenant_context
from v1.storefront import storefront_bp


def _payload(bundle, locale: str) -> dict:
    svc = BundleService()
    items = []
    for item in svc.items_for(bundle.id):
        product = (
            ProductService()
            .query_for_tenant(g.tenant_id)
            .filter_by(id=item.product_id)
            .first()
        )
        if not product:
            continue
        merged = TranslationService().merge_product(product, locale)
        price = Decimal(str(merged.get("price") or product.price or "0"))
        line = price * (Decimal("1") - Decimal(str(item.discount_percent)) / 100)
        items.append(
            {
                "product_id": product.id,
                "public_id": product.public_id,
                "name": merged.get("name") or product.name,
                "slug": merged.get("slug") or product.slug,
                "quantity": item.quantity,
                "discount_percent": str(item.discount_percent),
                "unit_price": str(line.quantize(Decimal("0.01"))),
                "line_total": str((line * item.quantity).quantize(Decimal("0.01"))),
                "image_url": product.image_url,
            }
        )
    original = sum(Decimal(str(i["line_total"])) for i in items)
    price = Decimal(str(bundle.bundle_price))
    data = dict(bundle.to_dict())
    data.update(
        {
            "items": items,
            "original_total": str(original.quantize(Decimal("0.01"))),
            "savings": str((original - price).quantize(Decimal("0.01"))),
        }
    )
    return data


def list_bundles(locale: str):
    try:
        tenant = require_tenant_context()
        rows = BundleService().list_published(tenant.id)
        return jsonify({"bundles": [_payload(b, locale) for b in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


def get_bundle(slug: str, locale: str):
    try:
        tenant = require_tenant_context()
        bundle = BundleService().get_published_by_slug(tenant.id, slug)
        if not bundle:
            raise NotFoundError("Bundle not found.")
        return jsonify({"bundle": _payload(bundle, locale)}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


def bundle_matches(bundle, query: str, locale: str):
    """Return bundle payload when it matches the search term, else None."""
    payload = _payload(bundle, locale)
    term = (query or "").strip().lower()
    if not term:
        return payload
    haystack = " ".join(
        [payload.get("name") or "", payload.get("description") or ""]
        + [i.get("name") or "" for i in payload.get("items", [])]
    ).lower()
    return payload if term in haystack else None


def bundle_cards(tenant_id: int) -> list[dict]:
    """Compact home-page bundle cards with localized names."""
    svc = BundleService()
    cards = []
    for b in svc.list_published(tenant_id):
        cards.append(
            {
                "name": b.name,
                "name_en": b.name_en,
                "slug": b.slug,
                "description": b.description,
                "image_url": b.image_url,
                "price": str(b.bundle_price),
                "max_per_order": b.max_per_order,
                "item_count": sum(x.quantity for x in svc.items_for(b.id)),
                "bundle_items": [
                    {
                        "name": getattr(
                            ProductService()
                            .query_for_tenant(tenant_id)
                            .filter_by(id=x.product_id)
                            .first()
                            or type("P", (), {"name": str(x.product_id)})(),
                            "name",
                        ),
                        "quantity": x.quantity,
                    }
                    for x in svc.items_for(b.id)
                ],
            }
        )
    return cards


def find_bundle_payload(tenant_id: int, slug: str, locale: str):
    """Payload for a published bundle, or None."""
    bundle = BundleService().get_published_by_slug(tenant_id, slug)
    return _payload(bundle, locale) if bundle else None
