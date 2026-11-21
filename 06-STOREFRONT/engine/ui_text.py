"""Small built-in dictionary for storefront UI chrome strings."""

from __future__ import annotations

_STRINGS: dict[str, dict[str, str]] = {
    "ar": {
        "home": "الرئيسية",
        "account": "حسابي",
        "cart": "السلة",
        "whatsapp": "واتساب",
        "products": "منتجاتنا",
        "no_products": "لا توجد منتجات منشورة بعد.",
        "category": "تصنيف",
        "no_category_products": "لا توجد منتجات في هذا التصنيف.",
        "no_image": "لا توجد صورة",
        "add_to_cart": "أضف للسلة",
        "order_whatsapp": "اطلب عبر واتساب",
        "view_cart": "عرض السلة",
        "out_of_stock": "نفد المخزون؟ اشترك ليصلك إشعار عند التوفر",
        "notify_me": "إشعرني",
        "shopping_cart": "سلة التسوق",
        "option_one": "الخيار 1",
        "option_two": "الخيار 2",
        "checkout": "إتمام الشراء",
        "checkout_desc": "الدفع الإلكتروني عبر بوابات الدفع المتاحة.",
        "whatsapp_order": "إرسال الطلب عبر واتساب",
        "whatsapp_desc": "نرسل ملخّص السلة كاملاً إلى المتجر، بدون بطاقة ائتمان.",
        "name_optional": "الاسم (اختياري)",
        "notes_optional": "ملاحظات (اختياري)",
        "your_email": "بريدك الإلكتروني",
        "order_request": "مرحباً، أريد طلب: ",
    },
    "en": {
        "home": "Home",
        "account": "Account",
        "cart": "Cart",
        "whatsapp": "WhatsApp",
        "products": "Our products",
        "no_products": "No published products yet.",
        "category": "Category",
        "no_category_products": "No products in this category.",
        "no_image": "No image",
        "add_to_cart": "Add to cart",
        "order_whatsapp": "Order via WhatsApp",
        "view_cart": "View cart",
        "out_of_stock": "Out of stock? Get notified when available",
        "notify_me": "Notify me",
        "shopping_cart": "Shopping cart",
        "option_one": "Option 1",
        "option_two": "Option 2",
        "checkout": "Checkout",
        "checkout_desc": "Pay online through the available payment gateways.",
        "whatsapp_order": "Send order via WhatsApp",
        "whatsapp_desc": "Send the whole cart summary to the store, no credit card.",
        "name_optional": "Name (optional)",
        "notes_optional": "Notes (optional)",
        "your_email": "Your email",
        "order_request": "Hello, I would like to order: ",
    },
}


def translate(key: str, locale: str = "ar") -> str:
    base = (locale or "ar").split("_")[0].lower()
    return _STRINGS.get(base, _STRINGS["ar"]).get(key, _STRINGS["ar"].get(key, key))
