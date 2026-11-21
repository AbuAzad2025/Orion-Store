"""WhatsApp deep-link helpers (no paid API, no external SDK)."""

from __future__ import annotations

import re
from urllib.parse import quote


def normalize_phone(value: str | None) -> str:
    """Return digits only, suitable for wa.me (also accepts +, spaces, dashes)."""
    if not value:
        return ""
    return re.sub(r"\D", "", value)


def whatsapp_url(phone: str | None, text: str = "") -> str:
    """Build a wa.me link, or an empty string when the store has no number."""
    number = normalize_phone(phone)
    if not number:
        return ""
    url = f"https://wa.me/{number}"
    if text:
        url += f"?text={quote(text)}"
    return url


def format_cart_order(
    store_name: str,
    items: list[dict],
    subtotal,
    customer_name: str = "",
    notes: str = "",
) -> str:
    """Build a tidy, Arabic order message from server-side cart data."""
    lines = [f"طلب جديد — {store_name}", "────────────────"]
    for index, item in enumerate(items, start=1):
        name = str(item.get("product_name") or item.get("product_id") or "منتج")
        quantity = item.get("quantity", 1)
        unit = item.get("unit_price", "0")
        total = item.get("total_price", "0")
        lines.append(f"{index}) {name}")
        lines.append(f"   {quantity} × {unit} = {total} ₪")
    lines.append("────────────────")
    lines.append(f"الإجمالي: {subtotal} ₪")
    if customer_name.strip():
        lines.append(f"الاسم: {customer_name.strip()}")
    if notes.strip():
        lines.append(f"ملاحظات: {notes.strip()}")
    lines.append("────────────────")
    lines.append("أُرسل عبر متجر Azadexa")
    return "\n".join(lines)
