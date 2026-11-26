"""Serve tenant product images from the external data directory.

Registered WITHOUT a url_prefix so the public URL stays
/store/static/images/products/<slug>/<filename>?store=<signed token>.
This route is more specific than the storefront static catch-all and must be
registered before it.
"""

from __future__ import annotations

import re
from pathlib import Path

from flask import Blueprint, abort, current_app, g, request, send_file

from core.store_token import resolve as resolve_store_token
from tenant.tenant import Tenant

store_image_serving_bp = Blueprint("store_image_serving", __name__)
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
# Safe filename: letters/digits/hyphen/underscore only, no dots or slashes,
# so path traversal is impossible. Covers both generated hex names and the
# descriptive names used by the seeded catalog.
FILE_RE = re.compile(r"[A-Za-z0-9_-]{1,80}\.(png|jpg|jpeg|webp|svg)")
MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def _images_root() -> Path:
    configured = current_app.config.get("PRODUCT_IMAGES_DIR") or ""
    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = Path(current_app.root_path).resolve().parents[3] / root
    return root.resolve()


@store_image_serving_bp.get("/store/static/images/products/<slug>/<filename>")
def serve_store_image(slug: str, filename: str):
    if not SLUG_RE.fullmatch(slug) or not FILE_RE.fullmatch(filename):
        abort(404)
    # Isolation: signed token for this store, or a logged-in same-tenant user.
    token_tenant = resolve_store_token(request.args.get("store", ""))
    allowed = token_tenant is not None and token_tenant.slug == slug
    if not allowed and g.user is not None and getattr(g.user, "tenant_id", None):
        user_tenant = Tenant.query.get(g.user.tenant_id)
        allowed = bool(user_tenant and user_tenant.slug == slug)
    if not allowed:
        abort(404)
    path = _images_root() / slug / filename
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype=MIME[Path(filename).suffix.lower()])
