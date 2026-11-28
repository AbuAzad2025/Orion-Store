"""Cart service — guest and authenticated carts (wave 3 #28)."""

from __future__ import annotations

import secrets
from decimal import Decimal

from catalog.product import Product
from core.exceptions import NotFoundError, ValidationError
from order.cart import Cart, CartItem
from orion.extensions import db


def _current_user_id() -> int | None:
    """Best-effort request user; service-only callers stay anonymous."""
    try:
        from flask import g, has_request_context

        if not has_request_context():
            return None
        user = getattr(g, "user", None)
        return user.id if user is not None else None
    except Exception:  # never block a cart write for a missing request context
        return None


def _resolve_customer_group_id(
    *, tenant_id: int, user_id: int | None, customer_group_id: int | None
) -> int | None:
    if customer_group_id is not None:
        return customer_group_id
    if user_id is None:
        return None
    from b2b.customer_group import CustomerGroupMember

    member = CustomerGroupMember.query.filter_by(
        tenant_id=tenant_id, user_id=user_id
    ).first()
    return member.customer_group_id if member else None


def _commit_keep_loaded() -> None:
    """Commit while keeping returned ORM instances readable after RLS binds."""
    session = db.session()
    previous = session.expire_on_commit
    session.expire_on_commit = False
    try:
        session.commit()
    finally:
        session.expire_on_commit = previous


class CartService:
    def get_or_create_cart(
        self, *, tenant_id: int, cart_token: str | None = None
    ) -> Cart:
        if cart_token:
            cart = Cart.query.filter_by(
                cart_token=cart_token, tenant_id=tenant_id, status="active"
            ).first()
            if cart:
                return cart
        cart = Cart(tenant_id=tenant_id, cart_token=secrets.token_urlsafe(24))
        db.session.add(cart)
        _commit_keep_loaded()
        return cart

    def get_cart(self, tenant_id: int, cart_token: str) -> Cart:
        cart = Cart.query.filter_by(
            cart_token=cart_token, tenant_id=tenant_id, status="active"
        ).first()
        if not cart:
            raise NotFoundError("Cart not found.")
        return cart

    def add_item(
        self,
        *,
        cart: Cart,
        product_id: int,
        quantity: int = 1,
        user_id: int | None = None,
        customer_group_id: int | None = None,
    ) -> CartItem:
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        product = Product.query.filter_by(
            id=product_id, tenant_id=cart.tenant_id, deleted_at=None
        ).first()
        if not product or not product.is_published:
            raise NotFoundError("Product not found.")
        existing = CartItem.query.filter_by(
            cart_id=cart.id, product_id=product_id
        ).first()
        required = existing.quantity + quantity if existing else quantity
        if product.quantity < required:
            raise ValidationError("Insufficient stock.")

        if user_id is None:
            user_id = _current_user_id()
        group_id = _resolve_customer_group_id(
            tenant_id=cart.tenant_id,
            user_id=user_id,
            customer_group_id=customer_group_id,
        )
        unit = product.price
        if group_id is not None:
            from b2b_svc.b2b_service import B2bService

            unit = B2bService().resolve_unit_price(
                tenant_id=cart.tenant_id,
                product_id=product_id,
                quantity=required,
                customer_group_id=group_id,
            )
        total = unit * quantity
        if existing:
            existing.quantity += quantity
            existing.unit_price = unit
            existing.total_price = unit * existing.quantity
            _commit_keep_loaded()
            return existing
        item = CartItem(
            cart_id=cart.id,
            tenant_id=cart.tenant_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit,
            total_price=total,
        )
        db.session.add(item)
        _commit_keep_loaded()
        return item

    def add_bundle(self, *, cart: Cart, bundle_id: int, quantity: int = 1) -> CartItem:
        """Add a published bundle as one line at its advertised price."""
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        from bundle.bundle import ProductBundle
        from bundle_svc.bundle_service import BundleService

        bundle = ProductBundle.query.filter_by(
            id=bundle_id, tenant_id=cart.tenant_id, is_published=True
        ).first()
        if bundle is None:
            raise NotFoundError("Bundle not found.")
        existing = CartItem.query.filter_by(
            cart_id=cart.id, bundle_id=bundle.id
        ).first()
        required = existing.quantity + quantity if existing else quantity
        if bundle.max_per_order is not None and required > bundle.max_per_order:
            raise ValidationError("Bundle limit per order exceeded.")
        for item in BundleService().items_for(bundle.id):
            product = Product.query.filter_by(
                id=item.product_id, tenant_id=cart.tenant_id, deleted_at=None
            ).first()
            if product is None:
                raise NotFoundError("Product not found.")
            if (product.quantity or 0) < item.quantity * required:
                raise ValidationError("Insufficient stock.")
        unit = Decimal(str(bundle.bundle_price))
        if existing:
            existing.quantity = required
            existing.unit_price = unit
            existing.total_price = unit * required
            _commit_keep_loaded()
            return existing
        item = CartItem(
            cart_id=cart.id,
            tenant_id=cart.tenant_id,
            bundle_id=bundle.id,
            quantity=quantity,
            unit_price=unit,
            total_price=unit * quantity,
        )
        db.session.add(item)
        _commit_keep_loaded()
        return item

    def list_items(self, cart: Cart) -> list[CartItem]:
        return CartItem.query.filter_by(cart_id=cart.id).all()

    def cart_subtotal(self, cart: Cart) -> Decimal:
        return sum((item.total_price for item in self.list_items(cart)), Decimal("0"))
