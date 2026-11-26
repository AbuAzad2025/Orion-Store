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
