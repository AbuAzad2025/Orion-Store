"""WhatsApp deep-link helpers (no paid API, no external SDK)."""

from __future__ import annotations

import re
from urllib.parse import quote

from core.i18n_messages import localize, request_locale


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
    locale: str | None = None,
) -> str:
    """Build a tidy, locale-aware order message from server-side cart data."""
    chosen = locale or request_locale()

    def tr(arabic: str, english: str) -> str:
        return localize(arabic, english, chosen)

    lines = [f"{tr('طلب جديد', 'New order')} — {store_name}", "────────────────"]
    for index, item in enumerate(items, start=1):
        name = str(
            item.get("product_name") or item.get("product_id") or tr("منتج", "Product")
        )
        quantity = item.get("quantity", 1)
        unit = item.get("unit_price", "0")
        total = item.get("total_price", "0")
        lines.append(f"{index}) {name}")
        lines.append(f"   {quantity} × {unit} = {total} ₪")
    lines.append("────────────────")
    lines.append(f"{tr('الإجمالي', 'Total')}: {subtotal} ₪")
    if customer_name.strip():
        lines.append(f"{tr('الاسم', 'Name')}: {customer_name.strip()}")
    if notes.strip():
        lines.append(f"{tr('ملاحظات', 'Notes')}: {notes.strip()}")
    lines.append("────────────────")
    lines.append(tr("أُرسل عبر متجر Azadexa", "Sent via Azadexa store"))
    return "\n".join(lines)


def _customer_lines(customer, tr) -> list[str]:
    """Append signed-in customer details when available."""
    if not customer:
        return []
    name = (
        " ".join(
            part
            for part in (
                getattr(customer, "first_name", None),
                getattr(customer, "last_name", None),
            )
            if part and str(part).strip()
        )
        or str(getattr(customer, "email", "") or "").strip()
    )
    lines = [
        "",
        f"\U0001f464 {tr('بيانات العميل', 'Customer details')}",
        f"{tr('الاسم', 'Name')}: {name}",
    ]
    email = str(getattr(customer, "email", "") or "").strip()
    if email:
        lines.append(f"{tr('البريد الإلكتروني', 'Email')}: {email}")
    return lines


def format_product_order(
    store_name: str,
    product_name: str,
    price,
    currency: str,
    customer=None,
    locale: str | None = None,
    quantity: int = 1,
) -> str:
    """Professional, ready-to-send WhatsApp order message for one product."""
    chosen = locale or request_locale()

    def tr(arabic: str, english: str) -> str:
        return localize(arabic, english, chosen)

    lines = [
        f"\U0001f6cd️ {tr('طلب جديد من', 'New order from')} {store_name}",
        "────────────────",
        f"\U0001f6d2 {tr('المنتج', 'Product')}: {product_name}",
        f"\U0001f4b0 {tr('السعر', 'Price')}: {price} {currency}",
        f"\U0001f501 {tr('الكمية', 'Quantity')}: {quantity}",
        "────────────────",
    ]
    lines.extend(_customer_lines(customer, tr))
    lines.extend(
        [
            "",
            tr(
                "هل يمكنكم تأكيد التوافر وتفاصيل الدفع والتوصيل؟ شكراً لاختياركم متجرنا 🌿",
                "Could you confirm availability, payment and delivery details? "
                "Thank you for choosing our store 🌿",
            ),
        ]
    )
    return "\n".join(lines)


def format_bundle_order(
    store_name: str,
    bundle_name: str,
    price,
    currency: str,
    customer=None,
    locale: str | None = None,
) -> str:
    """Professional WhatsApp order message for a product bundle."""
    chosen = locale or request_locale()
    message = format_product_order(
        store_name, bundle_name, price, currency, customer, chosen, 1
    )
    return message.replace(
        localize("\U0001f6d2 المنتج", "\U0001f6d2 Product", chosen),
        localize("\U0001f381 الحزمة", "\U0001f381 Bundle", chosen),
    )
