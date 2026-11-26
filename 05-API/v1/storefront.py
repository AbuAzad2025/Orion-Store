"""Storefront API — cart and checkout without payment (wave 3 #31)."""

from __future__ import annotations

from flask import Blueprint, Response, g, jsonify, request
from i18n_svc.translation_service import TranslationService
from shipping_svc.shipping_service import ShippingService

from catalog_svc.category_service import CategoryService
from catalog_svc.product_service import ProductService
from core.caching import (
    read_through_json,
    store_categories_list_key,
    store_product_detail_key,
    store_products_list_key,
)
from core.context import get_locale
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    OrionError,
)
from core.middleware import require_tenant_context
from core.pagination import paginate_query, paginated_payload, pagination_params
from core.rate_limit import limiter
from order_svc.cart_service import CartService
from order_svc.checkout_service import CheckoutService
from order_svc.order_service import OrderService
from payment_svc.payment_service import PaymentService
from tenant_gateway_svc.gateway_service import GatewayService
from v1.order_access import is_order_owner as _order_owner
from v1.order_access import order_access_token as _order_access_token
from v1.order_access import public_order_payload as _order_public_payload
from v1.order_access import verify_order_access_token as _verify_order_token
from v1.store_whatsapp import cart_items_with_names, register_store_whatsapp_routes

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
        locale = _locale()
        key = store_products_list_key(tenant.id, page, per_page, locale)

        def build():
            items, meta = paginate_query(
                _products.query_published(tenant.id), page, per_page
            )
            return paginated_payload(
                "products",
                items,
                meta,
                lambda p: _translations.merge_product(p, locale),
            )

        return jsonify(read_through_json(key, build)), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/bundles")
def list_bundles():
    from v1.store_bundles import list_bundles as _list

    return _list(_locale())


@storefront_bp.get("/bundles/<slug>")
def get_bundle(slug: str):
    from v1.store_bundles import get_bundle as _get

    return _get(slug, _locale())


@storefront_bp.get("/categories")
def list_categories():
    try:
        tenant = require_tenant_context()
        page, per_page = pagination_params()
        locale = _locale()
        key = store_categories_list_key(tenant.id, page, per_page, locale)

        def build():
            items, meta = paginate_query(
                _categories.query_for_tenant(tenant.id), page, per_page
            )
            return paginated_payload(
                "categories",
                items,
                meta,
                lambda c: _translations.merge_category(c, locale),
            )

        return jsonify(read_through_json(key, build)), 200
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
        locale = _locale()
        key = store_product_detail_key(tenant.id, slug, locale)

        def build():
            product = _products.get_by_slug(tenant.id, slug)
            return {"product": _translations.merge_product(product, locale)}

        return jsonify(read_through_json(key, build)), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/status")
def storefront_status():
    return {"blueprint": "storefront", "status": "active"}, 200


@storefront_bp.post("/cart")
@limiter.limit("30 per minute")
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
        items = cart_items_with_names(_carts, cart)
        return jsonify({"cart": cart.to_dict(), "items": items}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


register_store_whatsapp_routes(storefront_bp, _carts)


@storefront_bp.post("/cart/<cart_token>/items")
@limiter.limit("60 per minute")
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
@limiter.limit("10 per minute")
def checkout():
    try:
        tenant = require_tenant_context()
        data = request.get_json(silent=True) or {}
        cart = _carts.get_cart(tenant.id, data["cart_token"])
        customer = g.user
        is_registered_customer = bool(
            customer
            and customer.is_customer
            and not customer.is_admin
            and customer.tenant_id == tenant.id
        )
        # Never let a caller choose whose store credit gets debited.
        if is_registered_customer:
            customer_email = customer.email
        else:
            customer_email = data["customer_email"]
            if data.get("use_store_credit"):
                raise AuthorizationError(
                    "Store credit requires an authenticated customer account."
                )
        order = _checkout.checkout(
            cart=cart,
            customer_email=customer_email,
            user_id=customer.id if is_registered_customer else None,
            is_guest=not is_registered_customer,
            shipping_address=data.get("shipping_address", {}),
            idempotency_key=data.get("idempotency_key"),
            shipping_method_code=data.get("shipping_method_code"),
            voucher_code=data.get("voucher_code"),
            use_store_credit=bool(data.get("use_store_credit", False)),
        )
        from v1.storefront_pickup import book_pickup_for_order

        pickup = book_pickup_for_order(tenant.id, order, data)
        return (
            jsonify(
                {
                    "order": order.to_dict(),
                    "order_access_token": _order_access_token(order),
                    "pickup": pickup,
                }
            ),
            201,
        )
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
@limiter.limit("10 per minute")
def pay_order(public_id: str):
    try:
        tenant = require_tenant_context()
        order = _orders.get_by_public_id(tenant.id, public_id)
        data = request.get_json(silent=True) or {}
        capability = (
            request.headers.get("X-Order-Access-Token")
            or request.args.get("access_token")
            or data.get("order_access_token")
        )
        if not (_order_owner(order) or _verify_order_token(capability, order)):
            raise AuthorizationError("Permission denied.")
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
        return jsonify({"order": _order_public_payload(order)}), 200
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
        capability = request.headers.get("X-Order-Access-Token") or request.args.get(
            "access_token"
        )
        owner = _order_owner(order) or _verify_order_token(capability, order)
        if not owner:
            raise AuthorizationError("Permission denied.")
        payload = {"invoice": invoice.to_dict()}
        # The rendered HTML embeds the customer's email — only a verified
        # owner/admin should receive it, never a bare guest capability.
        if _order_owner(order):
            payload["rendered_html"] = invoice.rendered_html
        return jsonify(payload), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@storefront_bp.get("/orders/<public_id>/invoice.pdf")
def download_order_invoice_pdf(public_id: str):
    """Stream the stored invoice PDF to the order owner or a store admin."""
    try:
        from platform_models.invoice import Invoice
        from platform_svc.pdf_service import get_invoice_storage

        tenant = require_tenant_context()
        order = _orders.get_by_public_id(tenant.id, public_id)
        invoice = Invoice.query.filter_by(
            tenant_id=tenant.id, order_id=order.id
        ).first()
        if not invoice:
            raise NotFoundError("Invoice not found.")

        user = getattr(g, "user", None)
        if user is None:
            raise AuthenticationError("Authentication required.")
        is_admin = bool(
            getattr(g, "is_platform_admin", False)
            or (getattr(user, "is_admin", False) and user.tenant_id == tenant.id)
        )
        is_owner = (order.user_id is not None and order.user_id == user.id) or (
            order.customer_email or ""
        ).lower() == (getattr(user, "email", None) or "").lower()
        if not is_admin and not is_owner:
            raise AuthorizationError("Permission denied.")

        key = invoice.storage_key or invoice.pdf_artifact_path
        if not key:
            raise NotFoundError("Invoice PDF not found.")
        try:
            pdf = get_invoice_storage().get(key)
        except (KeyError, ValueError) as exc:
            raise NotFoundError("Invoice PDF not found.") from exc
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"',
            },
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
