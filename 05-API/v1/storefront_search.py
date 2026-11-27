"""GET /api/v1/store/search — text search + filters over published products."""

from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, jsonify, request
from i18n_svc.translation_service import TranslationService

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.context import get_locale
from core.exceptions import OrionError
from core.middleware import require_tenant_context
from core.pagination import paginate_query, pagination_params

storefront_search_bp = Blueprint("storefront_search", __name__)
_products = ProductService()
_categories = CategoryService()
_translations = TranslationService()


def _parse_decimal(value: str | None):
    if value is None or not value.strip():
        return None
    try:
        return Decimal(value.strip())
    except Exception:
        return None


@storefront_search_bp.get("/search")
def storefront_search():
    try:
        tenant = require_tenant_context()
        locale = get_locale()
        featured_raw = request.args.get("featured")
        featured = (
            featured_raw.strip().lower() in ("1", "true", "on", "yes")
            if featured_raw
            else None
        )
        sort = request.args.get("sort", "default")
        if sort not in _products.SORT_OPTIONS:
            sort = "default"
        category_id = None
        slug = request.args.get("category", "").strip()
        if slug:
            category_id = _categories.get_by_slug(tenant.id, slug).id
        page, per_page = pagination_params()
        q = request.args.get("q", "").strip()
        products, meta = paginate_query(
            _products.query_search_published(
                tenant.id,
                q,
                category_id=category_id,
                featured=featured,
                price_min=_parse_decimal(request.args.get("price_min")),
                price_max=_parse_decimal(request.args.get("price_max")),
                sort=sort,
            ),
            page,
            per_page,
        )
        from bundle_svc.bundle_service import BundleService

        from v1.store_bundles import bundle_matches

        query = request.args.get("q", "").strip()
        bundles = [
            bundle_matches(b, query, locale)
            for b in BundleService().list_published(tenant.id)
            if bundle_matches(b, query, locale) is not None
        ]
        return (
            jsonify(
                {
                    "products": [
                        _translations.merge_product(p, locale) for p in products
                    ],
                    "bundles": bundles,
                    "categories": [
                        c.to_dict() for c in _categories.list_for_tenant(tenant.id)
                    ],
                    "count": meta["total"],
                    "pagination": meta,
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
