"""Tenant sales and gross-profit report built from paid orders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from orion.extensions import db
from order.order import Order, OrderItem


def _money(value) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


class SalesReportService:
    def build(
        self,
        tenant_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        query = Order.query.filter_by(tenant_id=tenant_id, payment_status="paid")
        if date_from is not None:
            query = query.filter(Order.created_at >= date_from)
        if date_to is not None:
            query = query.filter(Order.created_at <= date_to)
        orders = query.order_by(Order.created_at.desc()).all()
        order_ids = [order.id for order in orders]
        items = (
            db.session.query(OrderItem)
            .filter(
                OrderItem.tenant_id == tenant_id,
                OrderItem.order_id.in_(order_ids),
            )
            .all()
            if order_ids
            else []
        )
        revenue = sum((order.total for order in orders), Decimal("0"))
        tax = sum((order.tax_amount for order in orders), Decimal("0"))
        discounts = sum((order.discount_amount for order in orders), Decimal("0"))
        shipping = sum((order.shipping_cost for order in orders), Decimal("0"))
        cogs = sum(
            (Decimal(str(item.unit_cost or 0)) * item.quantity for item in items),
            Decimal("0"),
        )
        net_sales = revenue - tax - shipping
        gross_profit = net_sales - cogs
        top: dict[str, dict] = {}
        for item in items:
            row = top.setdefault(
                item.product_name,
                {"name": item.product_name, "quantity": 0, "revenue": Decimal("0")},
            )
            row["quantity"] += item.quantity
            row["revenue"] += Decimal(str(item.total_price or 0))
        top_products = sorted(
            top.values(), key=lambda row: row["revenue"], reverse=True
        )[:10]
        return {
            "orders_count": len(orders),
            "revenue": _money(revenue),
            "tax": _money(tax),
            "discounts": _money(discounts),
            "shipping": _money(shipping),
            "cogs": _money(cogs),
            "net_sales": _money(net_sales),
            "gross_profit": _money(gross_profit),
            "margin_percent": _money(
                (gross_profit / net_sales * 100) if net_sales else Decimal("0")
            ),
            "top_products": [
                {
                    "name": row["name"],
                    "quantity": row["quantity"],
                    "revenue": _money(row["revenue"]),
                }
                for row in top_products
            ],
        }
