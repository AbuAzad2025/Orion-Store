"""HTML to PDF artifact generation (§0.13.6 — MVP sync path).

Arabic-safe rendering
---------------------
The legacy implementation did ``text.encode("ascii", "ignore")`` which silently
deleted every Arabic character before drawing it with the Latin-only Helvetica
core font.  We now:

1. strip markup while keeping *all* Unicode code points (``html_to_text``),
2. draw the text with an Arabic-capable Unicode TTF font found on the system,
3. let HarfBuzz shape the Arabic runs (joining + RTL) so the glyphs are correct
   *and* the PDF's ToUnicode map keeps the logical text extractable.

The public ``html_to_pdf(html) -> bytes`` signature is unchanged, and a
``generate_pdf`` alias is provided for callers that use that name.
"""

from __future__ import annotations

import abc
import html as html_lib
import os
import re
from pathlib import Path

from fpdf import FPDF

_DEFAULT_TEXT = "Azadexa Invoice"
_MAX_CHARS = 8000
_FONT_FAMILY = "orion-arabic"

# Ordered fallbacks: an explicit override first, then common Windows/Linux/macOS
# locations of fonts that contain Arabic glyphs (Arial Unicode MS is preferred).
_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\ARIALUNI.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def html_to_text(html: str) -> str:
    """Convert HTML to plain text without discarding non-ASCII characters."""
    text = re.sub(r"<script\b[^>]*>.*?</script\s*>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style\s*>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text, flags=re.UNICODE).strip()


def _find_unicode_font() -> str | None:
    """Return the first existing Arabic-capable TTF path, or ``None``."""
    override = os.environ.get("INVOICE_PDF_FONT") or os.environ.get("ORION_PDF_FONT")
    candidates = ([override] if override else []) + list(_FONT_CANDIDATES)

    # Optional, dependency-free portability boost when matplotlib happens to be
    # installed (it ships DejaVuSans.ttf, which includes Arabic glyphs).
    try:
        import matplotlib  # noqa: PLC0415 - optional soft dependency
    except ImportError:
        pass
    else:
        candidates.append(
            str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf")
        )

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def html_to_pdf(html: str) -> bytes:
    """Render HTML to PDF bytes, preserving Arabic text in the output."""
    text = html_to_text(html) or _DEFAULT_TEXT
    font_path = _find_unicode_font()

    if font_path is None:
        raise RuntimeError(
            "No Unicode TTF font with Arabic coverage was found. "
            "Set INVOICE_PDF_FONT to a .ttf path (e.g. DejaVuSans.ttf or "
            "NotoSansArabic-Regular.ttf). Refusing to silently drop Arabic text."
        )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font(_FONT_FAMILY, "", font_path)
    pdf.set_font(_FONT_FAMILY, size=10)

    # HarfBuzz gives correct Arabic joining/RTL and a logical ToUnicode map.
    # It is an optional runtime dependency (uharfbuzz); without it the glyphs
    # are still embedded, just without shaping.
    try:
        pdf.set_text_shaping(True)
    except Exception:  # pragma: no cover - depends on optional uharfbuzz
        pass

    pdf.multi_cell(0, 6, text[:_MAX_CHARS])
    return bytes(pdf.output())


def generate_pdf(html: str) -> bytes:
    """Backwards-compatible name for :func:`html_to_pdf`."""
    return html_to_pdf(html)


# ---------------------------------------------------------------------------
# Invoice object storage
# ---------------------------------------------------------------------------
# A deliberately small abstraction: invoices are opaque byte blobs addressed by
# a key.  The default backend is the local filesystem, so no paid/external
# object storage (e.g. S3) is required to run or self-host the platform.


class InvoiceStorage(abc.ABC):
    """Abstract object store for generated invoice PDFs."""

    @abc.abstractmethod
    def put(self, key: str, data: bytes) -> str:
        """Store ``data`` under ``key`` and return the persisted key."""

    @abc.abstractmethod
    def get(self, key: str) -> bytes:
        """Return the bytes stored under ``key`` (``KeyError`` when missing)."""


class LocalInvoiceStorage(InvoiceStorage):
    """Filesystem-backed object store rooted at ``instance/invoices``.

    Set ``INVOICE_STORAGE_DIR`` to relocate the root (the legacy
    ``INVOICE_ARTIFACT_DIR`` is still honoured as a fallback). Keys are relative
    paths; traversal outside the configured root is rejected.
    """

    DEFAULT_DIR = "instance/invoices"

    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        configured = (
            root
            or os.environ.get("INVOICE_STORAGE_DIR")
            or os.environ.get("INVOICE_ARTIFACT_DIR")
            or self.DEFAULT_DIR
        )
        self.root = Path(configured).expanduser().resolve()

    def _path_for(self, key: str) -> Path:
        if not key or not isinstance(key, str):
            raise ValueError("Invalid storage key.")
        target = (self.root / key).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Invalid storage key.") from exc
        return target

    def put(self, key: str, data: bytes) -> str:
        target = self._path_for(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes(data))
        return key

    def get(self, key: str) -> bytes:
        target = self._path_for(key)
        try:
            return target.read_bytes()
        except FileNotFoundError as exc:
            raise KeyError(key) from exc


_invoice_storage: InvoiceStorage | None = None


def set_invoice_storage(storage: InvoiceStorage | None) -> None:
    """Inject a storage backend (used by tests/ops); ``None`` restores default."""
    global _invoice_storage
    _invoice_storage = storage


def get_invoice_storage() -> InvoiceStorage:
    """Return the configured invoice object store.

    When no backend was injected, a fresh :class:`LocalInvoiceStorage` is
    created so ``INVOICE_STORAGE_DIR`` is honoured at call time.
    """
    if _invoice_storage is not None:
        return _invoice_storage
    return LocalInvoiceStorage()


__all__ = [
    "InvoiceStorage",
    "LocalInvoiceStorage",
    "generate_pdf",
    "get_invoice_storage",
    "html_to_pdf",
    "html_to_text",
    "set_invoice_storage",
]
