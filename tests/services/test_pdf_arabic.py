"""Arabic-preserving PDF generation (ASCII-stripping regression)."""

from __future__ import annotations

import io

from pypdf import PdfReader

from platform_svc.pdf_service import generate_pdf, html_to_pdf, html_to_text

ARABIC_TEMPLATE = (
    "<div><h1>فاتورة</h1><p>مرحبا بك في متجر أزادكسا</p></div>"
    '<footer id="azadexa-platform-footer" data-immutable="true">'
    "شكرا لتسوقكم"
    "</footer>"
)


def test_html_to_text_preserves_arabic() -> None:
    text = html_to_text(ARABIC_TEMPLATE)
    assert "فاتورة" in text
    assert "أزادكسا" in text
    assert "<h1>" not in text


def test_html_to_pdf_keeps_arabic_word() -> None:
    data = html_to_pdf(ARABIC_TEMPLATE)
    assert data.startswith(b"%PDF")

    reader = PdfReader(io.BytesIO(data))
    extracted = "".join(page.extract_text() or "" for page in reader.pages)
    assert "فاتورة" in extracted


def test_generate_pdf_alias_keeps_interface() -> None:
    assert generate_pdf(ARABIC_TEMPLATE).startswith(b"%PDF")
