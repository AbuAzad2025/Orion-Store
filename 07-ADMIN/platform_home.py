"""Public landing page for the platform domain (orion.azadexa.com/)."""

from __future__ import annotations

from pathlib import Path

from admin_locale import get_admin_locale, remember_admin_locale
from flask import (
    Blueprint,
    g,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from platform_svc.platform_settings_service import PlatformSettingsService
from tenant.tenant import Tenant

_ADMIN_ROOT = Path(__file__).resolve().parent

platform_home_bp = Blueprint(
    "platform_home",
    __name__,
    template_folder=str(_ADMIN_ROOT / "templates"),
)


@platform_home_bp.context_processor
def inject_platform_settings():
    try:
        settings = PlatformSettingsService().get_singleton()
    except Exception:
        settings = None
    return {"platform_settings": settings, "viewer_user": getattr(g, "user", None)}


@platform_home_bp.after_request
def remember_locale(response):
    return remember_admin_locale(response)


@platform_home_bp.get("/s/<slug>")
def short_store_link(slug: str):
    """Short, indexable store URL served directly (200) for SEO."""
    from engine.routes import render_store_index

    tenant = Tenant.query.filter_by(
        slug=slug, is_active=True, deleted_at=None
    ).first_or_404()
    return redirect(f"/s/{tenant.slug}/", code=301)


@platform_home_bp.get("/google8a1714ed6e039773.html")
def google_site_verification():
    resp = make_response("google-site-verification: google8a1714ed6e039773.html", 200)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


@platform_home_bp.get("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        "Disallow: /cart\n"
        "Disallow: /checkout\n"
        "Disallow: /account\n"
        "Disallow: /login\n"
        f"Sitemap: {request.host_url.rstrip('/')}/sitemap.xml\n"
    )
    resp = make_response(body, 200)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp


@platform_home_bp.get("/sitemap.xml")
def sitemap_xml():
    from core.store_token import issue as issue_store_token

    rows = (
        Tenant.query.filter_by(is_active=True, deleted_at=None)
        .order_by(Tenant.id)
        .all()
    )
    base = request.host_url.rstrip("/")
    from i18n.cms_page import CmsPage

    from catalog.category import Category
    from catalog.product import Product

    tenant_ids = [store.id for store in rows]
    products_by_tenant: dict[int, list[Product]] = {}
    categories_by_tenant: dict[int, list[Category]] = {}
    pages_by_tenant: dict[int, list[CmsPage]] = {}
    if tenant_ids:
        for product in (
            Product.query.filter_by(is_published=True, deleted_at=None)
            .filter(Product.tenant_id.in_(tenant_ids))
            .order_by(Product.tenant_id, Product.id)
            .all()
        ):
            products_by_tenant.setdefault(product.tenant_id, []).append(product)
        for category in (
            Category.query.filter(Category.tenant_id.in_(tenant_ids))
            .order_by(Category.tenant_id, Category.id)
            .all()
        ):
            categories_by_tenant.setdefault(category.tenant_id, []).append(category)
        for page in (
            CmsPage.query.filter_by(is_published=True)
            .filter(CmsPage.tenant_id.in_(tenant_ids))
            .order_by(CmsPage.tenant_id, CmsPage.id)
            .all()
        ):
            pages_by_tenant.setdefault(page.tenant_id, []).append(page)
    urls = [(f"{base}/", "daily", "1.0"), (f"{base}/?locale=en", "weekly", "0.8")]
    for store in rows:
        home = f"{base}/s/{store.slug}/"
        urls.append((home, "daily", "0.9"))
        for product in products_by_tenant.get(store.id, ()):
            urls.append((f"{home}product/{product.slug}", "weekly", "0.8"))
        for category in categories_by_tenant.get(store.id, ()):
            urls.append((f"{home}category/{category.slug}", "weekly", "0.6"))
        for page in pages_by_tenant.get(store.id, ()):
            urls.append((f"{home}pages/{page.slug}", "monthly", "0.4"))
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, freq, priority in urls:
        body.append(
            f"  <url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{priority}</priority></url>"
        )
    body.append("</urlset>")
    resp = make_response("\n".join(body), 200)
    resp.headers["Content-Type"] = "application/xml; charset=utf-8"
    return resp


@platform_home_bp.get("/")
def platform_home():
    # On a store subdomain, "/" belongs to the storefront, never to the platform.
    host = (request.host or "").split(":")[0].lower()
    if host != "orion.azadexa.com":
        from engine.routes import render_store_index

        return render_store_index()

    # One domain only: a signed store token on "/" renders that store's
    # storefront instead of the landing page.
    if request.args.get("store") or request.args.get("tenant_slug"):
        from engine.routes import render_store_index

        return render_store_index()

    locale = get_admin_locale()
    rows = (
        Tenant.query.filter_by(is_active=True, deleted_at=None)
        .order_by(Tenant.id)
        .all()
    )
    from core.store_token import issue as issue_store_token

    identity = {
        "palestinian-heritage": {
            "tagline": "تراث فلسطيني · منتجات من الأرض",
            "tagline_en": "Palestinian heritage · products from the land",
            "mark": "🇵🇸",
            "a": "#0f3d2e",
            "b": "#1c6347",
            "ink": "#f3e9c8",
            "pattern": "repeating-linear-gradient(45deg, rgba(255,255,255,.05) 0 8px, transparent 8px 16px)",
        },
    }

    def card(store):
        style = identity.get(
            store.slug,
            {
                "tagline": "",
                "mark": store.name[:1].upper(),
                "a": "#13233a",
                "b": "#1d3d5c",
                "ink": "#e9c77b",
                "pattern": "",
            },
        )
        return {
            "name": store.name,
            "name_en": store.name_en or store.slug,
            "slug": store.slug,
            "url": f"/s/{store.slug}/",
            "admin_url": f"/admin/login?tenant_slug={store.slug}",
            **style,
        }

    stores = [card(s) for s in rows]
    primary = stores[0] if stores else None
    store_url = primary["url"] if primary else "#"
    store_token = request.args.get("store", "")
    store_admin_url = primary["admin_url"] if primary else "/admin/login"
    account_url = f"/account?store={issue_store_token(rows[0])}" if rows else "#"
    return render_template(
        "platform_home.html",
        page_title="Azadexa Platform" if locale == "en" else "منصة Azadexa",
        stores=stores,
        locale=locale,
        store_url=store_url,
        store_token=store_token,
        store_admin_url=store_admin_url,
        account_url=account_url,
    )
