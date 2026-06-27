"""Admin static assets (wave 5 #50-51)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint

_ADMIN_ROOT = Path(__file__).resolve().parents[1]

admin_assets_bp = Blueprint(
    "admin_assets",
    __name__,
    static_folder=str(_ADMIN_ROOT / "static"),
    static_url_path="/admin/static",
)
