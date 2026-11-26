"""Storefront HTML pages — wave 5 #55-57."""

from __future__ import annotations

import re
from pathlib import Path

from compliance.compliance import CookieConsentSetting
from flask import Blueprint, g, request, url_for
from i18n_svc.page_service import PageService

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.context import get_locale
from core.exceptions import NotFoundError
from core.pagination import paginate_query, pagination_params
from engine.theme_engine import ThemeEngine
from engine.ui_text import translate

_STOREFRONT_ROOT = Path(__file__).resolve().parents[1]

storefront_ui_bp = Blueprint(
    "storefront_ui",
    __name__,
    template_folder=str(_STOREFRONT_ROOT / "themes" / "default" / "templates"),
)
_engine = ThemeEngine()
_products = ProductService()
_categories = CategoryService()
_pages = PageService()


@storefront_ui_bp.context_processor
def inject_footer_pages():
    """Published pages for the storefront footer (privacy/terms links).

    Titles follow the resolved request locale via the translation merge, but
    the canonical page slug is kept so footer links always resolve.
    """
    tenant = getattr(g, "tenant", None)
    if not tenant:
        return {"footer_pages": []}
    locale = get_locale()
    pages = []
    for page in _pages.list_published(tenant.id):
        data = _pages.merge_translation(page, locale)
        data["slug"] = page.slug
        pages.append(data)
    return {"footer_pages": pages}


def _tenant_or_404():
    if not g.tenant:
        return None
    return g.tenant


_HOSTNAME_RE = re.compile(r"^[a-z0-9.-]+$")


def _base_domain() -> str | None:
    """Registrable base domain from the current Host (demo.azadexa.com -> azadexa.com)."""
    host = (request.host or "").split(":")[0].lower()
    parts = host.split(".")
    if len(parts) >= 3:
        base = ".".join(parts[1:])
        return base if _HOSTNAME_RE.fullmatch(base) else None
    return None


def _store_admin_login_url(tenant) -> str:
    """Admin login on the store's own host so tenant resolution uses the Host.

    This lets a store admin log in without typing a slug. A same-host relative
    URL is the safe fallback when a base domain cannot be derived.
    """
    base = _base_domain()
    if tenant.custom_domain and _HOSTNAME_RE.fullmatch(tenant.custom_domain.lower()):
        host = tenant.custom_domain.lower()
    elif tenant.domain and base:
        host = f"{tenant.domain}.{base}"
    else:
        return "/admin/login"
    if not _HOSTNAME_RE.fullmatch(host):
        return "/admin/login"
    return f"https://{host}/admin/login"


def _platform_admin_login_url() -> str:
    """Dedicated platform-admin login, separate from every store."""
    base = _base_domain()
    return f"https://orion.{base}/admin/login" if base else "/admin/login"


def render_store_index():
    """Render the storefront home (shared with the platform root on store hosts)."""
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    from i18n_svc.translation_service import TranslationService

    locale = get_locale()
    ts = TranslationService()
    category_id = _parse_category_id(tenant.id, request.args.get("category"))
    featured = _parse_featured(request.args.get("featured"))
    sort = _parse_sort(request.args.get("sort"))
    price_min = _parse_decimal(request.args.get("price_min"))
    price_max = _parse_decimal(request.args.get("price_max"))
    products = _products.query_published(
        tenant.id,
        category_id=category_id,
        featured=featured,
        price_min=price_min,
        price_max=price_max,
        sort="featured" if sort == "default" else sort,
    ).all()
    products_i18n = [ts.merge_product(p, locale) for p in products]
    categories = _categories.list_for_tenant(tenant.id)
    counts = _categories.category_product_counts(tenant.id)
    from v1.store_bundles import bundle_cards

    bundles = bundle_cards(tenant.id)
    from core.store_token import issue as issue_store_token

    return _engine.render(
        "index.html",
        bundles=bundles,
        store_token=issue_store_token(tenant),
        tenant=tenant,
        products=products,
        products_i18n=products_i18n,
        page_title=tenant.name_for(locale),
        locale=locale,
        categories=categories,
        category_counts=counts,
        selected_category_id=category_id,
        featured=bool(featured),
        sort=sort,
        price_min=price_min,
        price_max=price_max,
    )


@storefront_ui_bp.get("/")
def store_index():
    return render_store_index()


@storefront_ui_bp.get("/s/<slug>/")
def store_index_clean(slug: str):
    return render_store_index()


@storefront_ui_bp.get("/s/<slug>/bundle/<bundle_slug>")
def store_bundle_detail(slug: str, bundle_slug: str):
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    from v1.store_bundles import find_bundle_payload

    locale = get_locale()
    bundle = find_bundle_payload(tenant.id, bundle_slug, locale)
    if not bundle:
        return "Bundle not found.", 404
    return _engine.render(
        "bundle.html",
        tenant=tenant,
        bundle=bundle,
        page_title=bundle["name"],
        locale=locale,
    )


@storefront_ui_bp.get("/s/<slug>/product/<product_slug>")
def store_product_clean(slug: str, product_slug: str):
    return store_product(product_slug)


@storefront_ui_bp.get("/s/<slug>/category/<category_slug>")
def store_category_clean(slug: str, category_slug: str):
    return store_category(category_slug)


@storefront_ui_bp.get("/product/<slug>")
def store_product(slug: str):
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    from i18n_svc.translation_service import TranslationService

    locale = get_locale()
    ts = TranslationService()
    product = ts.get_product_by_localized_slug(tenant.id, slug, locale)
    product_i18n = ts.merge_product(product, locale)
    from core.store_token import issue as issue_store_token

    structured = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product_i18n.get("name") or product.name,
        "image": ([product.image_url] if product.image_url else []),
        "offers": {
            "@type": "Offer",
            "price": str(product_i18n.get("price") or product.price),
            "priceCurrency": (tenant.default_currency or "ILS"),
            "availability": (
                "https://schema.org/InStock"
                if product.quantity > 0
                else "https://schema.org/OutOfStock"
            ),
        },
    }
    return _engine.render(
        "product.html",
        store_token=issue_store_token(tenant),
        tenant=tenant,
        product=product,
        product_i18n=product_i18n,
        page_title=product_i18n.get("name") or product.name,
        locale=locale,
        structured_data=structured,
    )


@storefront_ui_bp.get("/category/<slug>")
def store_category(slug: str):
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    from i18n_svc.translation_service import TranslationService

    locale = get_locale()
    ts = TranslationService()
    category = ts.get_category_by_localized_slug(tenant.id, slug, locale)
    category_i18n = ts.merge_category(category, locale)
    products = _products.query_published(
        tenant.id,
        category_id=category.id,
        featured=_parse_featured(request.args.get("featured")),
        price_min=_parse_decimal(request.args.get("price_min")),
        price_max=_parse_decimal(request.args.get("price_max")),
        sort=(
            "featured"
            if _parse_sort(request.args.get("sort")) == "default"
            else _parse_sort(request.args.get("sort"))
        ),
    ).all()
    products_i18n = [ts.merge_product(p, locale) for p in products]
    categories = _categories.list_for_tenant(tenant.id)
    counts = _categories.category_product_counts(tenant.id)
    return _engine.render(
        "category.html",
        tenant=tenant,
        category=category_i18n,
        products=products,
        products_i18n=products_i18n,
        page_title=category_i18n.get("name") or category.name,
        locale=locale,
        categories=categories,
        category_counts=counts,
        selected_category_id=category.id,
        featured=bool(_parse_featured(request.args.get("featured"))),
        sort=_parse_sort(request.args.get("sort")),
        price_min=_parse_decimal(request.args.get("price_min")),
        price_max=_parse_decimal(request.args.get("price_max")),
    )


@storefront_ui_bp.get("/login")
def store_login():
    """Unified sign-in entry: customer account or store admin on this store."""
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    locale = get_locale()
    return _engine.render(
        "login.html",
        tenant=tenant,
        page_title=translate("sign_in", locale),
        store_admin_login_url=_store_admin_login_url(tenant),
        platform_admin_login_url=_platform_admin_login_url(),
        locale=locale,
    )


def _parse_category_id(tenant_id: int, slug: str):
    from catalog.category import Category

    slug = (slug or "").strip()
    if not slug:
        return None
    category = Category.query.filter_by(
        tenant_id=tenant_id, slug=slug, deleted_at=None
    ).first()
    return category.id if category else None


def _parse_decimal(value: str | None):
    if value is None or not value.strip():
        return None
    try:
        from decimal import Decimal

        return Decimal(value.strip())
    except Exception:
        return None


def _parse_featured(value: str | None) -> bool | None:
    if value is None:
        return None
    return str(value).strip().lower() in ("1", "true", "on", "yes")


def _parse_sort(value: str | None) -> str:
    from catalog_svc.product_service import ProductService

    value = (value or "").strip()
    return value if value in ProductService.SORT_OPTIONS else "default"


@storefront_ui_bp.get("/s/<slug>/search")
def store_search_clean(slug: str):
    return store_search()


@storefront_ui_bp.get("/search")
def store_search():
    """Product search page: text search + category/featured/price/sort filters."""
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    from i18n_svc.translation_service import TranslationService

    locale = get_locale()
    ts = TranslationService()
    query = request.args.get("q", "").strip()
    category_id = _parse_category_id(tenant.id, request.args.get("category"))
    featured = _parse_featured(request.args.get("featured"))
    sort = _parse_sort(request.args.get("sort"))
    price_min = _parse_decimal(request.args.get("price_min"))
    price_max = _parse_decimal(request.args.get("price_max"))
    products_q = _products.query_search_published(
        tenant.id,
        query,
        category_id=category_id,
        featured=featured,
        price_min=price_min,
        price_max=price_max,
        sort=sort,
    )
    page, per_page = pagination_params()
    products, meta = paginate_query(products_q, page, per_page)
    products_i18n = [ts.merge_product(p, locale) for p in products]
    categories = _categories.list_for_tenant(tenant.id)
    counts = _categories.category_product_counts(tenant.id)
    from urllib.parse import quote as _quote

    keep_params = "".join(
        f"&{key}={_quote(request.args[key], safe='')}"
        for key in ("q", "category", "featured", "price_min", "price_max", "sort")
        if request.args.get(key)
    )

    def _page_url(n: int) -> str:
        params = {k: v for k, v in request.args.items()}
        params["page"] = str(n)
        return url_for("storefront_ui.store_search", **params)

    from bundle_svc.bundle_service import BundleService
    from v1.store_bundles import bundle_matches

    bundles = [
        b
        for b in (
            bundle_matches(bundle, query, locale)
            for bundle in BundleService().list_published(tenant.id)
        )
        if b is not None
    ]
    return _engine.render(
        "search.html",
        tenant=tenant,
        page_title=translate("search_results_title", locale),
        locale=locale,
        search_q=query,
        products=products,
        products_i18n=products_i18n,
        bundles=bundles,
        categories=categories,
        category_counts=counts,
        selected_category_id=category_id,
        featured=bool(featured),
        sort=sort,
        price_min=price_min,
        price_max=price_max,
        pagination_meta=meta,
        prev_url=_page_url(page - 1) if page > 1 else None,
        next_url=_page_url(page + 1) if page < meta["pages"] else None,
        keep_params=keep_params,
    )


@storefront_ui_bp.get("/account")
def store_account():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    return _engine.render(
        "account.html",
        tenant=tenant,
        page_title=translate("account", get_locale()),
        locale=get_locale(),
    )


@storefront_ui_bp.get("/cart")
def store_cart():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    return _engine.render(
        "cart.html",
        tenant=tenant,
        page_title=translate("cart", get_locale()),
        locale=get_locale(),
    )


@storefront_ui_bp.get("/checkout")
def store_checkout():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    return _engine.render(
        "checkout.html",
        tenant=tenant,
        page_title=translate("checkout", get_locale()),
        locale=get_locale(),
    )


@storefront_ui_bp.get("/consent")
def store_consent():
    """Public cookie-consent page driven by the tenant's compliance settings."""
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    setting = CookieConsentSetting.query.filter_by(tenant_id=tenant.id).first()
    return _engine.render(
        "consent.html",
        tenant=tenant,
        cookie_settings=setting,
        page_title=translate("privacy_cookies", get_locale()),
        locale=get_locale(),
    )


@storefront_ui_bp.get("/s/<slug>/pages/<page_slug>")
def store_page_clean(slug: str, page_slug: str):
    return store_page(page_slug)


@storefront_ui_bp.get("/pages/<slug>")
def store_page(slug: str):
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    locale = get_locale()
    try:
        page = _pages.get_by_slug(tenant.id, slug)
    except NotFoundError:
        return (
            _engine.render(
                "page.html",
                tenant=tenant,
                page=None,
                message=translate("page_not_found_desc", locale),
                page_title="404",
                locale=locale,
            ),
            404,
        )
    merged = _pages.merge_translation(page, locale)
    return _engine.render(
        "page.html",
        tenant=tenant,
        page=merged,
        page_title=merged["title"],
        locale=locale,
    )
