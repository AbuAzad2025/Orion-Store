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
    stores = (
        Tenant.query.filter_by(is_active=True, deleted_at=None)
        .order_by(Tenant.id)
        .all()
    )
    return render_template(
        "platform_home.html", page_title="منصة Azadexa", stores=stores
    )
