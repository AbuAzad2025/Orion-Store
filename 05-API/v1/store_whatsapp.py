"""WhatsApp cart-order endpoint and cart item enrichment for the storefront."""

from __future__ import annotations

from flask import jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from core.rate_limit import limiter
from engine.whatsapp import format_cart_order, whatsapp_url


def cart_items_with_names(carts, cart) -> list[dict]:
    """Cart items + product names in the language of the current request."""
    from i18n_svc.translation_service import TranslationService

    from catalog.product import Product
    from core.context import get_locale

    items = [item.to_dict() for item in carts.list_items(cart)]
    ids = [item["product_id"] for item in items]
    if ids:
        products = {
            p.id: p
            for p in Product.query.filter(
                Product.tenant_id == cart.tenant_id, Product.id.in_(ids)
            ).all()
        }
        locale = get_locale()
        translate = TranslationService()
        for item in items:
            product = products.get(item["product_id"])
            if product is None:
                item["product_name"] = str(item["product_id"])
                continue
            merged = translate.merge_product(product, locale)
            item["product_name"] = merged.get("name") or product.name
    return items


def register_store_whatsapp_routes(bp, carts) -> None:
    @bp.post("/cart/<cart_token>/whatsapp-message")
    @limiter.limit("10 per minute")
    def cart_whatsapp_message(cart_token: str):
        """Build a WhatsApp order message from server-side cart data."""
        try:
            tenant = require_tenant_context()
            if not tenant.phone:
                return jsonify({"error": "رقم واتساب غير مُضبط لهذا المتجر."}), 400
            cart = carts.get_cart(tenant.id, cart_token)
            items = cart_items_with_names(carts, cart)
            if not items:
                return jsonify({"error": "السلة فارغة."}), 400
            data = request.get_json(silent=True) or {}
            message = format_cart_order(
                tenant.name,
                items,
                carts.cart_subtotal(cart),
                customer_name=str(data.get("customer_name", "")),
                notes=str(data.get("notes", "")),
            )
            return (
                jsonify(
                    {"message": message, "url": whatsapp_url(tenant.phone, message)}
                ),
                200,
            )
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code
