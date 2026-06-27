"""Storefront API — cart and checkout without payment (wave 3 #31)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from i18n_svc.translation_service import TranslationService
from shipping_svc.shipping_service import ShippingService

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.context import get_locale
from core.exceptions import OrionError
from core.middleware import require_tenant_context
from core.pagination import paginate_query, paginated_payload, pagination_params
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from order_svc.order_service import OrderService
from payment_svc.payment_service import PaymentService
from tenant_gateway_svc.gateway_service import GatewayService

storefront_bp = Blueprint("storefront", __name__)
_carts = CartService()
_checkout = CheckoutService()
_orders = OrderService()
_payments = PaymentService()
_products = ProductService()
_categories = CategoryService()
_shipping = ShippingService()
_translations = TranslationService()
_gateways = GatewayService()


def _locale() -> str:
    return get_locale()


@storefront_bp.get("/products")
def list_products():
    try:
        tenant = require_tenant_context()
        page, per_page = pagination_params()
        items, meta = paginate_query(
            _products.query_published(tenant.id), page, per_page
        )
        return (
            jsonify(
                paginated_payload(
                    "products",
                    items,
                    meta,
                    lambda p: _translations.merge_product(p, _locale()),
                )
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/categories")
def list_categories():
    try:
        tenant = require_tenant_context()
        page, per_page = pagination_params()
        items, meta = paginate_query(
            _categories.query_for_tenant(tenant.id), page, per_page
        )
        return (
            jsonify(
                paginated_payload(
                    "categories",
                    items,
                    meta,
                    lambda c: _translations.merge_category(c, _locale()),
                )
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/categories/<slug>")
def get_category(slug: str):
    try:
        tenant = require_tenant_context()
        category = _translations.get_category_by_localized_slug(
            tenant.id, slug, _locale()
        )
        return (
            jsonify({"category": _translations.merge_category(category, _locale())}),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/products/<slug>")
def get_product(slug: str):
    try:
        tenant = require_tenant_context()
        product = _products.get_by_slug(tenant.id, slug)
        return (
            jsonify({"product": _translations.merge_product(product, _locale())}),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/status")
def storefront_status():
    return {"blueprint": "storefront", "status": "active"}, 200


@storefront_bp.post("/cart")
def create_cart():
    try:
        tenant = require_tenant_context()
        cart = _carts.get_or_create_cart(tenant_id=tenant.id)
        return jsonify({"cart": cart.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/cart/<cart_token>")
def get_cart(cart_token: str):
    try:
        tenant = require_tenant_context()
        cart = _carts.get_cart(tenant.id, cart_token)
        items = [_i.to_dict() for _i in _carts.list_items(cart)]
        return jsonify({"cart": cart.to_dict(), "items": items}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.post("/cart/<cart_token>/items")
def add_cart_item(cart_token: str):
    try:
        tenant = require_tenant_context()
        cart = _carts.get_cart(tenant.id, cart_token)
        data = request.get_json(silent=True) or {}
        item = _carts.add_item(
            cart=cart,
            product_id=int(data["product_id"]),
            quantity=int(data.get("quantity", 1)),
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@storefront_bp.get("/shipping/methods")
def list_shipping_methods():
    try:
        tenant = require_tenant_context()
        methods = _shipping.list_methods(tenant.id)
        return jsonify({"methods": [m.to_dict() for m in methods]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.post("/checkout")
def checkout():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        cart = _carts.get_cart(tenant.id, data["cart_token"])
        order = _checkout.checkout(
            cart=cart,
            customer_email=data["customer_email"],
            shipping_address=data.get("shipping_address", {}),
            idempotency_key=data.get("idempotency_key"),
            shipping_method_code=data.get("shipping_method_code"),
            voucher_code=data.get("voucher_code"),
        )
        return jsonify({"order": order.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing required fields."}), 400


@storefront_bp.get("/payment-methods")
def list_payment_methods():
    try:
        tenant = require_tenant_context()
        methods = _gateways.list_enabled_for_checkout(tenant.id)
        return jsonify({"payment_methods": methods}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.post("/orders/<public_id>/pay")
def pay_order(public_id: str):
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        result = _payments.pay_order(
            tenant_id=tenant.id,
            order_public_id=public_id,
            payment_method=data.get("payment_method", "cod"),
        )
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/orders/<public_id>")
def get_order(public_id: str):
    try:
        tenant = require_tenant_context()
        order = _orders.get_by_public_id(tenant.id, public_id)
        return jsonify({"order": order.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/orders/<public_id>/invoice")
def get_order_invoice(public_id: str):
    try:
        from platform_models.invoice import Invoice

        tenant = require_tenant_context()
        order = _orders.get_by_public_id(tenant.id, public_id)
        invoice = Invoice.query.filter_by(
            tenant_id=tenant.id, order_id=order.id
        ).first()
        if not invoice:
            return jsonify({"error": "Invoice not found."}), 404
        return (
            jsonify(
                {
                    "invoice": invoice.to_dict(),
                    "rendered_html": invoice.rendered_html,
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
