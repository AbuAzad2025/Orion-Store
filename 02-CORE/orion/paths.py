"""Centralised data paths that must live OUTSIDE the application source tree.

Every reader and writer of product images resolves through this module so a
misconfigured relative value or a pre-planted symlink cannot redirect uploads
or reads outside the dedicated data directory.
"""

from __future__ import annotations

import re
from pathlib import Path

from flask import current_app

from core.exceptions import ValidationError

SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")


def source_root() -> Path:
    """Absolute path of the deployed application source root."""
    return Path(current_app.root_path).resolve().parents[2]


def images_root() -> Path:
    """Resolve PRODUCT_IMAGES_DIR to an absolute, contained data directory."""
    configured = current_app.config.get("PRODUCT_IMAGES_DIR") or ""
    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = source_root().parent / root
    root = root.resolve()
    source = source_root()
    if root == source or source in root.parents:
        raise ValidationError(
            "Image storage must be outside the application source tree."
        )
    return root


def store_folder(slug: str) -> Path:
    """Create (or fetch) the 0750 folder for one store, rejecting symlinks."""
    if not SLUG_RE.fullmatch(slug):
        raise ValidationError("Invalid store.")
    root = images_root()
    if root.is_symlink():
        raise ValidationError("Invalid image storage.")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    folder = root / slug
    if folder.is_symlink():
        raise ValidationError("Invalid image storage.")
    folder.mkdir(parents=True, exist_ok=True, mode=0o750)
    try:
        folder.chmod(0o750)
    except OSError:
        pass
    return folder
