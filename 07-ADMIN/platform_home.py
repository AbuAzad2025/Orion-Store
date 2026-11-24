"""Public landing page for the platform domain (orion.azadexa.com/)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, g, make_response, render_template, request, url_for

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


@platform_home_bp.get("/s/<slug>")
def short_store_link(slug: str):
    """Short, indexable store URL served directly (200) for SEO."""
    from engine.routes import render_store_index

    tenant = Tenant.query.filter_by(
        slug=slug, is_active=True, deleted_at=None
    ).first_or_404()
    g.tenant = tenant
    g.tenant_id = tenant.id
    return render_store_index()


@platform_home_bp.get("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /$\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        "Disallow: /*?store=\n"
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
    urls = [(f"{base}/", "daily", "1.0"), (f"{base}/?locale=en", "weekly", "0.8")]
    for store in rows:
        urls.append((f"{base}/s/{store.slug}", "weekly", "0.9"))
        urls.append((f"{base}/?store={issue_store_token(store)}", "never", "0.1"))
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

    locale = (request.args.get("locale") or "ar").strip().lower()
    if locale not in ("ar", "en"):
        locale = "ar"
    rows = (
        Tenant.query.filter_by(is_active=True, deleted_at=None)
        .order_by(Tenant.id)
        .all()
    )
    from core.store_token import issue as issue_store_token

    identity = {
        "demo": {
            "tagline": "Azadexa Demo · منتج متنوع",
            "mark": "A",
            "a": "#13233a",
            "b": "#1d3d5c",
            "ink": "#e9c77b",
            "pattern": "",
        },
        "palestinian-heritage": {
            "tagline": "تراث فلسطيني · منتجات من الأرض",
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
            "slug": store.slug,
            "url": f"/s/{store.slug}",
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
