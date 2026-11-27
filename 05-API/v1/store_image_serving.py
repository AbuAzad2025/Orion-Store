"""Serve product images from the external data directory.

Registered WITHOUT a url_prefix so the public URL stays
/store/static/images/products/<slug>/<filename>?store=<signed token>.
The route is more specific than the storefront static catch-all.
"""

from __future__ import annotations

import re
from pathlib import Path

from flask import Blueprint, abort, current_app, g, request, send_file

from core.store_token import resolve as resolve_store_token
from orion.paths import SLUG_RE, images_root
from tenant.tenant import Tenant

store_image_serving_bp = Blueprint("store_image_serving", __name__)
# Generated uploads are hex-named; seeded catalogue art uses descriptive names.
# SVG is allowed only because every response carries a strict CSP (and SVG
# responses get their own sandboxed CSP), so inline <script> cannot execute.
FILENAME_RE = re.compile(r"[A-Za-z0-9_-]{1,80}\.(png|jpg|jpeg|webp|svg)")
MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


@store_image_serving_bp.get("/store/static/images/products/<slug>/<filename>")
def serve_store_image(slug: str, filename: str):
    if not SLUG_RE.fullmatch(slug) or not FILENAME_RE.fullmatch(filename):
        abort(404)
    # Isolation: signed token for this store, or a logged-in same-tenant user.
    token_tenant = resolve_store_token(request.args.get("store", ""))
    allowed = token_tenant is not None and token_tenant.slug == slug
    if not allowed and g.user is not None and getattr(g.user, "tenant_id", None):
        user_tenant = Tenant.query.get(g.user.tenant_id)
        allowed = bool(user_tenant and user_tenant.slug == slug)
    if not allowed:
        abort(404)
    root = images_root()
    candidate = root / slug / filename
    if candidate.is_symlink():
        abort(404)
    path = candidate.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        abort(404)
    ext = Path(filename).suffix.lower()
    response = send_file(path, mimetype=MIME[ext])
    if ext == ".svg":
        # Defence in depth: even if a future CSP regression re-enables inline
        # scripts, an SVG navigated to directly cannot run scripts.
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response
