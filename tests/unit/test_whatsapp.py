"""WhatsApp deep-link helper — free wa.me links, no external API."""

from __future__ import annotations

from engine.whatsapp import format_cart_order, normalize_phone, whatsapp_url


def test_normalize_phone() -> None:
    assert normalize_phone("+970 (50) 123-4567") == "970501234567"
    assert normalize_phone(None) == ""


def test_whatsapp_url_encodes_message() -> None:
    url = whatsapp_url("+970501234567", "مرحباً، أريد طلب: منتج")
    assert url.startswith("https://wa.me/970501234567?text=")
    assert "%D9%85%D8%B1%D8%AD%D8%A8" in url


def test_empty_phone_yields_no_link() -> None:
    assert whatsapp_url("") == ""
    assert whatsapp_url(None, "hello") == ""


def test_cart_order_message_is_organized() -> None:
    items = [
        {
            "product_name": "منتج أ",
            "quantity": 2,
            "unit_price": "15.00",
            "total_price": "30.00",
        },
        {
            "product_name": "منتج ب",
            "quantity": 1,
            "unit_price": "20.00",
            "total_price": "20.00",
        },
    ]
    message = format_cart_order(
        "متجر تجريبي", items, "50.00", customer_name="أحمد", notes="التوصيل غداً"
    )
    assert message.startswith("طلب جديد — متجر تجريبي")
    assert "1) منتج أ" in message
    assert "2 × 15.00 = 30.00" in message
    assert "الإجمالي: 50.00 ₪" in message
    assert "الاسم: أحمد" in message
    assert "ملاحظات: التوصيل غداً" in message
