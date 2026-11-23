"""Storefront HTML pages — wave 5 #55-57."""

from __future__ import annotations

import re
from pathlib import Path

from compliance.compliance import CookieConsentSetting
from flask import Blueprint, g, request
from i18n_svc.page_service import PageService

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.context import get_locale
from core.exceptions import NotFoundError
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


@storefront_ui_bp.get("/")
def store_index():
    tenant = _tenant_or_404()
    if not tenant:
        return "Store not found.", 404
    from i18n_svc.translation_service import TranslationService

    locale = get_locale()
    products = _products.list_published(tenant.id)
    # Sort the MODEL list once; the translated list is derived in the same order
    # so index.html can safely pair them by loop index (slug/image/cart-id come
    # from the model, display strings from the merged dict).
    products.sort(key=lambda p: (not p.is_featured, p.name or ""))
    ts = TranslationService()
    products_i18n = [ts.merge_product(p, locale) for p in products]
    return _engine.render(
        "index.html",
        tenant=tenant,
        products=products,
        products_i18n=products_i18n,
        page_title=tenant.name,
        locale=locale,
    )


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
    return _engine.render(
        "product.html",
        tenant=tenant,
        product=product,
        product_i18n=product_i18n,
        page_title=product_i18n.get("name") or product.name,
        locale=locale,
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
    products = [
        p for p in _products.list_published(tenant.id) if p.category_id == category.id
    ]
    # Keep the two lists index-aligned — see store_index.
    products.sort(key=lambda p: (not p.is_featured, p.name or ""))
    products_i18n = [ts.merge_product(p, locale) for p in products]
    return _engine.render(
        "category.html",
        tenant=tenant,
        category=category_i18n,
        products=products,
        products_i18n=products_i18n,
        page_title=category_i18n.get("name") or category.name,
        locale=locale,
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
