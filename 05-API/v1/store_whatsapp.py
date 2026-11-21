"""WhatsApp cart-order endpoint and cart item enrichment for the storefront."""

from __future__ import annotations

from flask import jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from core.rate_limit import limiter
from engine.whatsapp import format_cart_order, whatsapp_url


def cart_items_with_names(carts, cart) -> list[dict]:
    """Cart items + real product names (CartItem.to_dict has ids only)."""
    from catalog.product import Product

    items = [item.to_dict() for item in carts.list_items(cart)]
    ids = [item["product_id"] for item in items]
    if ids:
        names = dict(
            Product.query.filter(
                Product.tenant_id == cart.tenant_id, Product.id.in_(ids)
            ).with_entities(Product.id, Product.name).all()
        )
        for item in items:
            item["product_name"] = names.get(item["product_id"], str(item["product_id"]))
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
                jsonify({"message": message, "url": whatsapp_url(tenant.phone, message)}),
                200,
            )
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code
