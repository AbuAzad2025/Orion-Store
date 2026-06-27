"""HTML to PDF artifact generation (§0.13.6 — MVP sync path)."""

from __future__ import annotations

import re

from fpdf import FPDF


def html_to_pdf(html: str) -> bytes:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.encode("ascii", "ignore").decode("ascii") or "Azadexa Invoice"
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 5, text[:8000] or "Invoice")
    return bytes(pdf.output())
