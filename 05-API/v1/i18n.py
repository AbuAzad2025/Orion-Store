"""i18n public API (wave 7 #60)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from i18n_svc.i18n_service import I18nService

from core.exceptions import OrionError

i18n_bp = Blueprint("i18n", __name__)
_i18n = I18nService()


@i18n_bp.get("/languages")
def list_languages():
    try:
        locales = _i18n.list_active_locales()
        return jsonify({"languages": [loc.to_dict() for loc in locales]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
