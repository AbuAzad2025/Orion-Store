"""Tenant-scoped product image upload and serving.

Images are stored OUTSIDE the application source tree in a configurable data
directory (Config.PRODUCT_IMAGES_DIR / PRODUCT_IMAGES_DIR env var) so they
survive release swaps. The public URL shape stays unchanged and is served by
this blueprint, with strict per-store isolation.
"""

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
URL_PREFIX = "/store/static/images/products/"


def _images_root() -> Path:
    """Configurable data directory, always outside the application source."""
    configured = current_app.config.get("PRODUCT_IMAGES_DIR") or ""
    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = Path(current_app.root_path).resolve().parents[3] / root
    return root.resolve()


def _tenant_for_write():
    """Write target is ALWAYS the authenticated user's own tenant."""
    uid = getattr(g.user, "tenant_id", None) if g.user else None
    if not uid:
        raise ValidationError("A store account is required to upload images.")
    tenant = Tenant.query.get(uid)
    if not tenant or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", tenant.slug):
        raise ValidationError("Invalid store.")
    return tenant


def _folder(slug: str) -> Path:
    folder = _images_root() / slug
    # mode 0750: owner (service user) can write; group read; others none.
    folder.mkdir(parents=True, exist_ok=True, mode=0o750)
    try:
        folder.chmod(0o750)
    except OSError:
        pass
    return folder


def _valid_image(ext: str, raw: bytes) -> bool:
    if ext == ".png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return raw.startswith(b"\xff\xd8\xff")
    if ext == ".webp":
        return raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
    return False


def _verify_image(path: Path) -> None:
    """Extra validation with Pillow when available (defense in depth)."""
    try:
        from PIL import Image
    except ImportError:
        return
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:  # noqa: BLE001 - any decode failure is invalid
        path.unlink(missing_ok=True)
        raise ValidationError("Image failed validation.") from exc


@product_images_bp.post("/upload")
def upload_product_image():
    try:
        require_tenant_admin()
        tenant = _tenant_for_write()
        file = request.files.get("image")
        if not file or not file.filename:
            raise ValidationError("No image file.")
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED or file.mimetype != ALLOWED[ext]:
            raise ValidationError("Only PNG, JPG or WEBP images are allowed.")
        raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValidationError("Image is too large (max 5MB).")
        if not _valid_image(ext, raw):
            raise ValidationError("File content is not a valid image.")
        name = secrets.token_hex(12) + ext
        path = _folder(tenant.slug) / name
        path.write_bytes(raw)
        try:
            path.chmod(0o640)
        except OSError:
            pass
        _verify_image(path)
        return (
            jsonify(
                {
                    "url": (
                        f"{URL_PREFIX}{tenant.slug}/{name}"
                        f"?store={issue_store_token(tenant)}"
                    )
                }
            ),
            201,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
