"""Storefront static assets."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint

_STOREFRONT_ROOT = Path(__file__).resolve().parents[1]

storefront_assets_bp = Blueprint(
    "storefront_assets",
    __name__,
    static_folder=str(_STOREFRONT_ROOT / "themes" / "default" / "static"),
    static_url_path="/store/static",
)
