"""Cart service — guest and authenticated carts (wave 3 #28)."""

from __future__ import annotations

import secrets
from decimal import Decimal

from catalog.product import Product
from core.exceptions import NotFoundError, ValidationError
from order.cart import Cart, CartItem
from orion.extensions import db


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
        db.session.commit()
        return cart

    def get_cart(self, tenant_id: int, cart_token: str) -> Cart:
        cart = Cart.query.filter_by(
            cart_token=cart_token, tenant_id=tenant_id, status="active"
        ).first()
        if not cart:
            raise NotFoundError("Cart not found.")
        return cart

    def add_item(self, *, cart: Cart, product_id: int, quantity: int = 1) -> CartItem:
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        product = Product.query.filter_by(
            id=product_id, tenant_id=cart.tenant_id, deleted_at=None
        ).first()
        if not product or not product.is_published:
            raise NotFoundError("Product not found.")
        if product.quantity < quantity:
            raise ValidationError("Insufficient stock.")
        unit = product.price
        total = unit * quantity
        existing = CartItem.query.filter_by(
            cart_id=cart.id, product_id=product_id
        ).first()
        if existing:
            existing.quantity += quantity
            existing.total_price = existing.unit_price * existing.quantity
            db.session.commit()
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
        db.session.commit()
        return item

    def list_items(self, cart: Cart) -> list[CartItem]:
        return CartItem.query.filter_by(cart_id=cart.id).all()

    def cart_subtotal(self, cart: Cart) -> Decimal:
        return sum((item.total_price for item in self.list_items(cart)), Decimal("0"))
