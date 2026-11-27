"""WhatsApp deep-link helpers (no paid API, no external SDK).

All generated messages use real store/customer data and explicit Unicode
bidirectional marks so Arabic (RTL) and English (LTR) render correctly next to
numbers, prices and email addresses.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from core.i18n_messages import localize, request_locale

RLM = "\u200f"  # right-to-left mark
LRM = "\u200e"  # left-to-right mark
FSI = "\u2068"  # first strong isolate (LTR content inside RTL text)
PDI = "\u2069"  # pop directional isolate
RLI = "\u2067"  # right-to-left isolate (RTL content inside LTR text)


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


def _is_rtl(locale: str | None) -> bool:
    return str(locale or "ar").lower().startswith(("ar", "he", "fa", "ur"))


def _bidi(value, rtl: bool) -> str:
    """Isolate a value so mixed Arabic/Latin text keeps its correct direction."""
    text = str(value or "")
    if not text:
        return ""
    has_arabic = any("\u0600" <= char <= "\u06ff" for char in text)
    if rtl:
        if has_arabic:
            return RLM + text + RLM
        return FSI + text + PDI
    if has_arabic:
        return RLI + text + PDI
    return text


def _wrap(text: str, rtl: bool) -> str:
    return (RLM if rtl else LRM) + text


def format_cart_order(
    store_name: str,
    items: list[dict],
    subtotal,
    customer_name: str = "",
    notes: str = "",
    locale: str | None = None,
    currency: str = "ILS",
    total=None,
) -> str:
    """Build a tidy, locale-aware order message from server-side cart data."""
    chosen = locale or request_locale()
    rtl = _is_rtl(chosen)
    code = (currency or "ILS").upper()
    symbol = {"ILS": "₪"}.get(code, code)
    grand_total = total if total is not None else subtotal

    def tr(arabic: str, english: str) -> str:
        return localize(arabic, english, chosen)

    lines = [
        f"{tr('طلب جديد', 'New order')} — {_bidi(store_name, rtl)}",
        "────────────────",
    ]
    for index, item in enumerate(items, start=1):
        name = str(
            item.get("product_name") or item.get("product_id") or tr("منتج", "Product")
        )
        quantity = item.get("quantity", 1)
        unit = item.get("unit_price", "0")
        total = item.get("total_price", "0")
        lines.append(f"{index}) {_bidi(name, rtl)}")
        lines.append(f"   {_bidi(f'{quantity} × {unit} = {total} {symbol}', rtl)}")
    lines.append("────────────────")
    lines.append(f"{tr('الإجمالي', 'Total')}: {_bidi(f'{grand_total} {symbol}', rtl)}")
    if customer_name.strip():
        lines.append(f"{tr('الاسم', 'Name')}: {_bidi(customer_name.strip(), rtl)}")
    if notes.strip():
        lines.append(f"{tr('ملاحظات', 'Notes')}: {_bidi(notes.strip(), rtl)}")
    lines.append("────────────────")
    lines.append(tr("أُرسل عبر متجر Azadexa", "Sent via Azadexa store"))
    return _wrap("\n".join(lines), rtl)


def _customer_lines(customer, tr, rtl: bool) -> list[str]:
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
        f"{tr('الاسم', 'Name')}: {_bidi(name, rtl)}",
    ]
    email = str(getattr(customer, "email", "") or "").strip()
    if email:
        lines.append(f"{tr('البريد الإلكتروني', 'Email')}: {_bidi(email, rtl)}")
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
    rtl = _is_rtl(chosen)

    def tr(arabic: str, english: str) -> str:
        return localize(arabic, english, chosen)

    lines = [
        f"\U0001f6cd️ {tr('طلب جديد من', 'New order from')} {_bidi(store_name, rtl)}",
        "────────────────",
        f"\U0001f6d2 {tr('المنتج', 'Product')}: {_bidi(product_name, rtl)}",
        f"\U0001f4b0 {tr('السعر', 'Price')}: {_bidi(f'{price} {currency}', rtl)}",
        f"\U0001f501 {tr('الكمية', 'Quantity')}: {_bidi(quantity, rtl)}",
        "────────────────",
    ]
    lines.extend(_customer_lines(customer, tr, rtl))
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
    return _wrap("\n".join(lines), rtl)


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


def format_store_inquiry(
    store_name: str, customer=None, locale: str | None = None
) -> str:
    """Professional general store inquiry used in header/footer buttons."""
    chosen = locale or request_locale()
    rtl = _is_rtl(chosen)

    def tr(arabic: str, english: str) -> str:
        return localize(arabic, english, chosen)

    lines = [
        f"\U0001f6cd️ {tr('مرحباً', 'Hello')} {_bidi(store_name, rtl)} \U0001f44b",
        tr(
            "أود الاستفسار عن منتجاتكم وتفاصيل الطلب والتوصيل.",
            "I would like to inquire about your products, ordering and delivery.",
        ),
        "────────────────",
    ]
    lines.extend(_customer_lines(customer, tr, rtl))
    lines.extend(
        [
            "",
            tr("شكراً لوقتكم 🌿", "Thank you for your time 🌿"),
        ]
    )
    return _wrap("\n".join(lines), rtl)
