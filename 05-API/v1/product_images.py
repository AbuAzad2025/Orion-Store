"""Tenant-scoped product image upload.

Images are written ONLY into the configured data directory, never into the
application source tree. Every upload is fully decoded and re-encoded before
it lands on disk, so polyglots, truncated files, decompression bombs and
metadata payloads cannot survive.
"""

from __future__ import annotations

import os
import secrets
import tempfile
from io import BytesIO
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request

from core.exceptions import OrionError, ValidationError
from core.middleware import require_tenant_admin
from core.rate_limit import limiter
from core.store_token import issue as issue_store_token
from orion.paths import images_root, store_folder
from tenant.tenant import Tenant

product_images_bp = Blueprint("product_images", __name__)
ALLOWED = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
PIL_FORMAT = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
MAGIC = {
    ".png": lambda raw: raw.startswith(b"\x89PNG\r\n\x1a\n"),
    ".jpg": lambda raw: raw.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda raw: raw.startswith(b"\xff\xd8\xff"),
    ".webp": lambda raw: raw.startswith(b"RIFF") and raw[8:12] == b"WEBP",
}
MAX_BYTES = 5 * 1024 * 1024
URL_PREFIX = "/store/static/images/products/"


def _tenant_for_write() -> Tenant:
    """Write target is ALWAYS the authenticated user's own tenant."""
    uid = getattr(g.user, "tenant_id", None) if g.user else None
    if not uid:
        raise ValidationError("A store account is required to upload images.")
    tenant = Tenant.query.get(uid)
    if tenant is None:
        raise ValidationError("Invalid store.")
    # store_folder() applies the strict slug regex and containment checks.
    store_folder(tenant.slug)
    return tenant


def _normalise_image(raw: bytes, ext: str) -> bytes:
    """Decode fully, then re-encode to strip polyglot/metadata payloads."""
    try:
        from PIL import Image, ImageFile, ImageOps
    except ImportError as exc:  # fail closed if Pillow is unavailable
        raise ValidationError("Server cannot validate images right now.") from exc
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    Image.MAX_IMAGE_PIXELS = 10_000_000
    expected = PIL_FORMAT[ext]
    try:
        with Image.open(BytesIO(raw)) as opened:
            if opened.format != expected:
                raise ValidationError("File content is not a valid image.")
            opened.load()  # full decode — rejects truncated/malformed data
            image = ImageOps.exif_transpose(opened)
            out = BytesIO()
            kwargs = {"format": expected}
            if expected == "JPEG":
                kwargs["quality"] = 92
            image.save(out, **kwargs)
            clean = out.getvalue()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("Image failed validation.") from exc
    if not clean or len(clean) > MAX_BYTES:
        raise ValidationError("Image is too large after validation.")
    return clean


def _write_atomic(folder: Path, data: bytes, ext: str) -> str:
    """Create the final file 0640 via an atomic rename, never following links."""
    fd, tmp = tempfile.mkstemp(prefix=".upload-", suffix=ext, dir=folder)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, 0o640)
        while True:
            name = secrets.token_hex(12) + ext
            destination = folder / name
            if not destination.exists() and not destination.is_symlink():
                break
        os.replace(tmp, destination)
        return name
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@product_images_bp.post("/upload")
@limiter.limit("20 per hour;5 per minute")
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
        if not MAGIC[ext](raw):
            raise ValidationError("File content is not a valid image.")
        clean = _normalise_image(raw, ext)
        folder = store_folder(tenant.slug)
        if not images_root().is_dir():
            raise ValidationError("Image storage is unavailable.")
        name = _write_atomic(folder, clean, ext)
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
