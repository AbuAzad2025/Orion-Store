"""Platform admin API (wave 2 settings)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

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


@platform_settings_bp.put("/settings")
def update_platform_settings():
    try:
        require_platform_admin()
        data = request.get_json(silent=True) or {}
        row = _settings.update_singleton(
            platform_name=data.get("platform_name"),
            owner_name=data.get("owner_name"),
            support_email=data.get("support_email"),
            default_currency=data.get("default_currency"),
            default_language=data.get("default_language"),
        )
        return jsonify({"settings": row.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
