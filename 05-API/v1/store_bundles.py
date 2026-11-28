"""Public storefront bundle endpoints — published bundles only."""

from __future__ import annotations

from decimal import Decimal

from bundle_svc.bundle_service import BundleService
from flask import g, jsonify
from i18n.product_translation import ProductTranslation

from bundle.bundle import BundleItem
from catalog.product import Product
from catalog_svc.product_service import ProductService
from core.exceptions import NotFoundError, OrionError
from core.middleware import require_tenant_context
from v1.storefront import storefront_bp


def preload_bundle_data(bundles, tenant_id: int, locale: str | None = None):
    """Batch bundle items, their products and (optionally) translations."""
    bundle_ids = [b.id for b in bundles]
    items = (
        BundleItem.query.filter(BundleItem.bundle_id.in_(bundle_ids))
        .order_by(BundleItem.id)
        .all()
        if bundle_ids
        else []
    )
    items_by_bundle: dict[int, list[BundleItem]] = {}
    for item in items:
        items_by_bundle.setdefault(item.bundle_id, []).append(item)
    product_ids = list({item.product_id for item in items})
    products = (
        {
            p.id: p
            for p in ProductService()
            .query_for_tenant(tenant_id)
            .filter(Product.id.in_(product_ids))
            .all()
        }
        if product_ids
        else {}
    )
    translations = (
        {
            t.product_id: t
            for t in ProductTranslation.query.filter(
                ProductTranslation.tenant_id == tenant_id,
                ProductTranslation.product_id.in_(product_ids),
                ProductTranslation.locale == locale,
            ).all()
        }
        if locale and product_ids
        else {}
    )
    return items_by_bundle, products, translations


def _payload(bundle, locale: str, loaded=None) -> dict:
    if loaded is None:
        loaded = preload_bundle_data([bundle], g.tenant_id, locale)
    items_by_bundle, products, translations = loaded
    items = []
    for item in items_by_bundle.get(bundle.id, []):
        product = products.get(item.product_id)
        if not product:
            continue
        trans = translations.get(product.id)
        price = Decimal(str(product.to_dict()["price"] or product.price or "0"))
        line = price * (Decimal("1") - Decimal(str(item.discount_percent)) / 100)
        items.append(
            {
                "product_id": product.id,
                "public_id": product.public_id,
                "name": (trans.name if trans else None) or product.name,
                "slug": (trans.slug if trans else None) or product.slug,
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
        loaded = preload_bundle_data(rows, tenant.id, locale)
        return jsonify({"bundles": [_payload(b, locale, loaded) for b in rows]}), 200
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


def bundle_matches(bundle, query: str, locale: str, loaded=None):
    """Return bundle payload when it matches the search term, else None."""
    payload = _payload(bundle, locale, loaded)
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
    bundles = svc.list_published(tenant_id)
    items_by_bundle, products, _ = preload_bundle_data(bundles, tenant_id)
    cards = []
    for b in bundles:
        bundle_items = items_by_bundle.get(b.id, [])
        cards.append(
            {
                "name": b.name,
                "name_en": b.name_en,
                "slug": b.slug,
                "description": b.description,
                "image_url": b.image_url,
                "price": str(b.bundle_price),
                "max_per_order": b.max_per_order,
                "item_count": sum(x.quantity for x in bundle_items),
                "bundle_items": [
                    {
                        "name": getattr(
                            products.get(x.product_id)
                            or type("P", (), {"name": str(x.product_id)})(),
                            "name",
                        ),
                        "quantity": x.quantity,
                    }
                    for x in bundle_items
                ],
            }
        )
    return cards


def find_bundle_payload(tenant_id: int, slug: str, locale: str):
    """Payload for a published bundle, or None."""
    bundle = BundleService().get_published_by_slug(tenant_id, slug)
    return _payload(bundle, locale) if bundle else None
