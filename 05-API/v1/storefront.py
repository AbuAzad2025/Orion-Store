"""Storefront API — cart and checkout without payment (wave 3 #31)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_context
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from order_svc.order_service import OrderService

storefront_bp = Blueprint("storefront", __name__)
_carts = CartService()
_checkout = CheckoutService()
_orders = OrderService()


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
        )
        return jsonify({"order": order.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing required fields."}), 400


@storefront_bp.get("/orders/<public_id>")
def get_order(public_id: str):
    try:
        tenant = require_tenant_context()
        order = _orders.get_by_public_id(tenant.id, public_id)
        return jsonify({"order": order.to_dict()}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
