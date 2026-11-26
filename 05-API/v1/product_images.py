"""Tenant-scoped product image upload — admins upload from their own device."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request

from core.exceptions import OrionError, ValidationError
from core.middleware import require_tenant_admin
from core.store_token import issue as issue_store_token
from tenant.tenant import Tenant

product_images_bp = Blueprint("product_images", __name__)
ALLOWED = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
MAX_BYTES = 5 * 1024 * 1024


def _store_slug() -> str:
    from tenant.tenant import Tenant

    # Never trust X-Tenant-ID for writes: use the authenticated user's tenant.
    uid = getattr(g.user, "tenant_id", None) if g.user else None
    if not uid:
        raise ValidationError("A store account is required to upload images.")
    tenant = Tenant.query.get(uid)
    if not tenant or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", tenant.slug):
        raise ValidationError("Invalid store.")
    return tenant.slug


def _folder() -> Path:
    root = Path(current_app.root_path).resolve().parents[1]
    folder = (
        root / "06-STOREFRONT/themes/default/static/images/products" / _store_slug()
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@product_images_bp.post("/upload")
def upload_product_image():
    try:
        require_tenant_admin()
        file = request.files.get("image")
        if not file or not file.filename:
            raise ValidationError("No image file.")
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED or file.mimetype != ALLOWED[ext]:
            raise ValidationError("Only PNG, JPG or WEBP images are allowed.")
        raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValidationError("Image is too large (max 5MB).")
        signatures = {
            ".png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
            ".jpg": raw.startswith(b"\xff\xd8\xff"),
            ".jpeg": raw.startswith(b"\xff\xd8\xff"),
            ".webp": raw.startswith(b"RIFF") and raw[8:12] == b"WEBP",
        }
        if not signatures[ext]:
            raise ValidationError("File content is not a valid image.")
        name = secrets.token_hex(12) + ext
        path = _folder() / name
        path.write_bytes(raw)
        return (
            jsonify(
                {
                    "url": (
                        f"/store/static/images/products/{_store_slug()}/{name}"
                        f"?store={issue_store_token(Tenant.query.get(g.tenant_id))}"
                    )
                }
            ),
            201,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
