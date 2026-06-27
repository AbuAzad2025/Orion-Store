"""B2B wholesale pricing and quotes (wave 9 #63)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from b2b.customer_group import CustomerGroup, CustomerGroupMember
from b2b.price_list import PriceList, PriceListItem
from b2b.quote import Quote, QuoteItem
from catalog.product import Product
from core.exceptions import NotFoundError, ValidationError
from order.order import Order, OrderEvent, OrderItem
from orion.extensions import db


class B2bService:
    def create_customer_group(
        self,
        *,
        tenant_id: int,
        name: str,
        code: str,
        discount_percent: str | Decimal = "0",
        payment_terms_days: int = 0,
        is_wholesale: bool = False,
        price_list_id: int | None = None,
    ) -> CustomerGroup:
        row = CustomerGroup(
            tenant_id=tenant_id,
            name=name,
            code=code.strip().lower(),
            discount_percent=Decimal(str(discount_percent)),
            payment_terms_days=payment_terms_days,
            is_wholesale=is_wholesale,
            price_list_id=price_list_id,
        )
        db.session.add(row)
        db.session.commit()
        return row

    def list_customer_groups(self, tenant_id: int) -> list[CustomerGroup]:
        return CustomerGroup.query.filter_by(tenant_id=tenant_id).all()

    def add_group_member(self, *, tenant_id: int, group_id: int, user_id: int) -> None:
        group = CustomerGroup.query.filter_by(id=group_id, tenant_id=tenant_id).first()
        if not group:
            raise NotFoundError("Customer group not found.")
        existing = CustomerGroupMember.query.filter_by(
            customer_group_id=group_id, user_id=user_id
        ).first()
        if not existing:
            db.session.add(
                CustomerGroupMember(
                    customer_group_id=group_id,
                    user_id=user_id,
                    tenant_id=tenant_id,
                )
            )
            db.session.commit()

    def create_price_list(self, *, tenant_id: int, name: str) -> PriceList:
        row = PriceList(tenant_id=tenant_id, name=name)
        db.session.add(row)
        db.session.commit()
        return row

    def add_price_item(
        self,
        *,
        tenant_id: int,
        price_list_id: int,
        product_id: int,
        price: str | Decimal,
        min_quantity: int = 1,
    ) -> PriceListItem:
        pl = PriceList.query.filter_by(id=price_list_id, tenant_id=tenant_id).first()
        if not pl:
            raise NotFoundError("Price list not found.")
        item = PriceListItem(
            price_list_id=price_list_id,
            product_id=product_id,
            price=Decimal(str(price)),
            min_quantity=min_quantity,
        )
        db.session.add(item)
        db.session.commit()
        return item

    def resolve_unit_price(
        self,
        *,
        tenant_id: int,
        product_id: int,
        quantity: int,
        customer_group_id: int | None = None,
    ) -> Decimal:
        product = Product.query.filter_by(id=product_id, tenant_id=tenant_id).first()
        if not product:
            raise NotFoundError("Product not found.")
        base = Decimal(str(product.price))
        group = None
        if customer_group_id:
            group = CustomerGroup.query.filter_by(
                id=customer_group_id, tenant_id=tenant_id
            ).first()
        if group and group.price_list_id:
            item = (
                PriceListItem.query.filter_by(
                    price_list_id=group.price_list_id, product_id=product_id
                )
                .filter(PriceListItem.min_quantity <= quantity)
                .order_by(PriceListItem.min_quantity.desc())
                .first()
            )
            if item:
                base = item.price
        if group and group.discount_percent > 0:
            base = (base * (1 - group.discount_percent / Decimal("100"))).quantize(
                Decimal("0.01")
            )
        return base

    def create_quote(
        self,
        *,
        tenant_id: int,
        customer_group_id: int | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Quote:
        quote = Quote(
            tenant_id=tenant_id,
            quote_number=f"QT-{tenant_id}-{uuid.uuid4().hex[:8].upper()}",
            customer_group_id=customer_group_id,
            user_id=user_id,
            notes=notes,
            status="draft",
        )
        db.session.add(quote)
        db.session.commit()
        return quote

    def add_quote_item(
        self,
        *,
        tenant_id: int,
        quote_id: int,
        product_id: int,
        quantity: int,
        discount_percent: str | Decimal = "0",
    ) -> QuoteItem:
        quote = Quote.query.filter_by(id=quote_id, tenant_id=tenant_id).first()
        if not quote:
            raise NotFoundError("Quote not found.")
        if quote.status != "draft":
            raise ValidationError("Quote is not editable.")
        unit = self.resolve_unit_price(
            tenant_id=tenant_id,
            product_id=product_id,
            quantity=quantity,
            customer_group_id=quote.customer_group_id,
        )
        item = QuoteItem(
            quote_id=quote.id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit,
            discount_percent=Decimal(str(discount_percent)),
        )
        db.session.add(item)
        db.session.flush()
        self._recalc_quote(quote)
        db.session.commit()
        return item

    def convert_quote_to_order(
        self,
        *,
        tenant_id: int,
        quote_id: int,
        customer_email: str,
        shipping_address: dict | None = None,
    ) -> Order:
        quote = Quote.query.filter_by(id=quote_id, tenant_id=tenant_id).first()
        if not quote:
            raise NotFoundError("Quote not found.")
        if quote.status == "converted":
            raise ValidationError("Quote already converted.")
        items = QuoteItem.query.filter_by(quote_id=quote.id).all()
        if not items:
            raise ValidationError("Quote has no items.")

        order = Order(
            tenant_id=tenant_id,
            order_number=f"ORD-B2B-{uuid.uuid4().hex[:8].upper()}",
            customer_email=customer_email.strip().lower(),
            shipping_address=shipping_address or {},
            subtotal=quote.subtotal,
            tax_amount=quote.tax_amount,
            total=quote.total_amount,
            status="pending",
            payment_status="pending",
        )
        db.session.add(order)
        db.session.flush()

        for qi in items:
            prod = Product.query.filter_by(
                id=qi.product_id, tenant_id=tenant_id
            ).first()
            if not prod or prod.quantity < qi.quantity:
                db.session.rollback()
                raise ValidationError("Insufficient stock for quote conversion.")
            prod.quantity -= qi.quantity
            line = qi.unit_price * qi.quantity
            discount = line * (qi.discount_percent / Decimal("100"))
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    tenant_id=tenant_id,
                    product_id=qi.product_id,
                    product_name=prod.name,
                    product_sku=prod.sku,
                    unit_price=qi.unit_price,
                    quantity=qi.quantity,
                    total_price=line - discount,
                )
            )

        quote.status = "converted"
        quote.converted_order_id = order.id
        db.session.add(
            OrderEvent(
                order_id=order.id,
                tenant_id=tenant_id,
                event_type="order.created",
                message=f"Created from quote {quote.quote_number}.",
            )
        )
        db.session.commit()
        return order

    def _recalc_quote(self, quote: Quote) -> None:
        items = QuoteItem.query.filter_by(quote_id=quote.id).all()
        subtotal = Decimal("0")
        for qi in items:
            line = qi.unit_price * qi.quantity
            discount = line * (qi.discount_percent / Decimal("100"))
            subtotal += line - discount
        quote.subtotal = subtotal
        quote.tax_amount = Decimal("0")
        quote.total_amount = subtotal
