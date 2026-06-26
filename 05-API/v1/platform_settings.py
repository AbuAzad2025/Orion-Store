"""Platform admin API (wave 2 settings)."""

from __future__ import annotations

from flask import Blueprint, jsonify

from core.exceptions import OrionError
from core.middleware import require_platform_admin
from platform_svc.platform_settings_service import PlatformSettingsService

platform_settings_bp = Blueprint("platform_settings", __name__)
_settings = PlatformSettingsService()


@platform_settings_bp.get("/settings")
def get_platform_settings():
    try:
        require_platform_admin()
        row = _settings.get_singleton()
        return jsonify({"settings": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
