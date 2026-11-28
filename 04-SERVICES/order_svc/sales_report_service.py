"""Tenant sales and gross-profit report built from paid orders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func

from orion.extensions import db

from order.order import Order, OrderItem  # isort: skip


def _money(value) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


class SalesReportService:
    def build(
        self,
        tenant_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        def _paid_orders(query):
            query = query.filter(
                Order.tenant_id == tenant_id,
                Order.payment_status == "paid",
            )
            if date_from is not None:
                query = query.filter(Order.created_at >= date_from)
            if date_to is not None:
                query = query.filter(Order.created_at <= date_to)
            return query

        totals = _paid_orders(
            db.session.query(
                func.count(Order.id).label("orders_count"),
                func.coalesce(func.sum(Order.total), 0).label("revenue"),
                func.coalesce(func.sum(Order.tax_amount), 0).label("tax"),
                func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
                func.coalesce(func.sum(Order.shipping_cost), 0).label("shipping"),
            )
        ).one()

        cogs = (
            _paid_orders(
                db.session.query(
                    func.coalesce(func.sum(OrderItem.unit_cost * OrderItem.quantity), 0)
                ).join(Order, Order.id == OrderItem.order_id)
            )
            .filter(OrderItem.tenant_id == tenant_id)
            .scalar()
        )

        top_rows = (
            _paid_orders(
                db.session.query(
                    OrderItem.product_name,
                    func.sum(OrderItem.quantity).label("quantity"),
                    func.sum(OrderItem.total_price).label("revenue"),
                ).join(Order, Order.id == OrderItem.order_id)
            )
            .filter(OrderItem.tenant_id == tenant_id)
            .group_by(OrderItem.product_name)
            .order_by(
                func.sum(OrderItem.total_price).desc(), OrderItem.product_name.asc()
            )
            .limit(10)
            .all()
        )

        revenue = Decimal(str(totals.revenue or 0))
        tax = Decimal(str(totals.tax or 0))
        discounts = Decimal(str(totals.discounts or 0))
        shipping = Decimal(str(totals.shipping or 0))
        cogs = Decimal(str(cogs or 0))
        net_sales = revenue - tax - shipping
        gross_profit = net_sales - cogs
        return {
            "orders_count": totals.orders_count,
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
                    "name": row.product_name,
                    "quantity": row.quantity,
                    "revenue": _money(row.revenue),
                }
                for row in top_rows
            ],
        }
