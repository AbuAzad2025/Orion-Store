"""Public landing page for the platform domain (orion.azadexa.com/)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, g, render_template

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


@platform_home_bp.get("/")
def platform_home():
    from flask import request

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

    def card(store):
        return {
            "name": store.name,
            "slug": store.slug,
            "url": f"/?store={issue_store_token(store)}",
            "admin_url": f"/admin/login?tenant_slug={store.slug}",
        }

    stores = [card(s) for s in rows]
    primary = stores[0] if stores else None
    store_url = primary["url"] if primary else "#"
    store_token = request.args.get("store", "")
    store_admin_url = primary["admin_url"] if primary else "/admin/login"
    account_url = (
        f"/account?store={issue_store_token(rows[0])}" if rows else "#"
    )
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
