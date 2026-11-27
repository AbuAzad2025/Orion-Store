"""WhatsApp cart-order endpoint and cart item enrichment for the storefront."""

from __future__ import annotations

from flask import jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from core.rate_limit import limiter
from engine.whatsapp import format_cart_order, format_product_order, whatsapp_url
from order_svc.whatsapp_order_service import WhatsAppOrderService


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
    orders = WhatsAppOrderService()

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
                customer_name=str(data.get("customer_name") or ""),
                notes=str(data.get("notes") or ""),
            )
            return (
                jsonify(
                    {"message": message, "url": whatsapp_url(tenant.phone, message)}
                ),
                200,
            )
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code

    @bp.post("/cart/<cart_token>/whatsapp-order")
    @limiter.limit("10 per minute")
    def cart_whatsapp_order(cart_token: str):
        """Create a pending manual order, then return the WhatsApp message."""
        try:
            tenant = require_tenant_context()
            if not tenant.phone:
                return jsonify({"error": "رقم واتساب غير مُضبط لهذا المتجر."}), 400
            cart = carts.get_cart(tenant.id, cart_token)
            items = cart_items_with_names(carts, cart)
            if not items:
                return jsonify({"error": "السلة فارغة."}), 400
            data = request.get_json(silent=True) or {}
            customer_name = str(data.get("customer_name") or "")
            notes = str(data.get("notes") or "")
            order = orders.create(
                tenant,
                items,
                customer_name=customer_name,
                customer_email=str(data.get("email") or ""),
                notes=notes,
            )
            message = format_cart_order(
                tenant.name, items, carts.cart_subtotal(cart), customer_name, notes
            )
            return (
                jsonify(
                    {
                        "message": message,
                        "url": whatsapp_url(tenant.phone, message),
                        "order": {
                            "public_id": str(order.public_id),
                            "order_number": order.order_number,
                        },
                    }
                ),
                201,
            )
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid request."}), 400

    @bp.post("/product/<int:product_id>/whatsapp-order")
    @limiter.limit("10 per minute")
    def product_whatsapp_order(product_id: int):
        """Create a pending single-product order from a product WhatsApp button."""
        try:
            tenant = require_tenant_context()
            if not tenant.phone:
                return jsonify({"error": "رقم واتساب غير مُضبط لهذا المتجر."}), 400
            data = request.get_json(silent=True) or {}
            from catalog.product import Product
            from core.context import get_locale

            product = Product.query.filter_by(
                id=product_id, tenant_id=tenant.id, deleted_at=None
            ).first()
            if product is None or not product.is_published:
                return jsonify({"error": "المنتج غير متاح."}), 404
            customer_name = str(data.get("customer_name") or "")
            order = orders.create(
                tenant,
                [
                    {
                        "product_id": product_id,
                        "quantity": int(data.get("quantity") or 1),
                    }
                ],
                customer_name=customer_name,
                customer_email=str(data.get("email") or ""),
                notes=str(data.get("notes") or ""),
            )
            message = format_product_order(
                tenant.name,
                product.name,
                str(product.price),
                tenant.default_currency or "ILS",
                None,
                get_locale(),
                int(data.get("quantity") or 1),
            )
            return (
                jsonify(
                    {
                        "message": message,
                        "url": whatsapp_url(tenant.phone, message),
                        "order": {
                            "public_id": str(order.public_id),
                            "order_number": order.order_number,
                        },
                    }
                ),
                201,
            )
        except OrionError as exc:
            return jsonify({"error": exc.message}), exc.status_code
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid request."}), 400
