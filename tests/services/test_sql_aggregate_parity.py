"""Parity guards for the SQL-aggregate report rewrites (round 11).

Compares the rewritten aggregates with a verbatim Python reference of the
original algorithms, using the standard test app (SQLite in emergency mode,
PostgreSQL in CI). Response shape must be identical.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from catalog.product import Product
from order.order import Order, OrderItem
from order_svc.sales_report_service import SalesReportService
from orion.extensions import db
from tenant_svc.tenant_service import TenantService


def _money(value) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


def _legacy_report(tenant_id):
    orders = Order.query.filter_by(tenant_id=tenant_id, payment_status="paid").all()
    ids = [o.id for o in orders]
    items = (
        OrderItem.query.filter(
            OrderItem.tenant_id == tenant_id, OrderItem.order_id.in_(ids)
        ).all()
        if ids
        else []
    )
    revenue = sum((o.total for o in orders), Decimal("0"))
    tax = sum((o.tax_amount for o in orders), Decimal("0"))
    shipping = sum((o.shipping_cost for o in orders), Decimal("0"))
    discounts = sum((o.discount_amount for o in orders), Decimal("0"))
    cogs = sum(
        (Decimal(str(i.unit_cost or 0)) * i.quantity for i in items), Decimal("0")
    )
    net = revenue - tax - shipping
    gross = net - cogs
    top: dict[str, dict] = {}
    for i in items:
        row = top.setdefault(
            i.product_name, {"n": i.product_name, "q": 0, "r": Decimal("0")}
        )
        row["q"] += i.quantity
        row["r"] += Decimal(str(i.total_price or 0))
    ranked = sorted(top.values(), key=lambda r: r["r"], reverse=True)[:10]
    return {
        "orders_count": len(orders),
        "revenue": _money(revenue),
        "tax": _money(tax),
        "discounts": _money(discounts),
        "shipping": _money(shipping),
        "cogs": _money(cogs),
        "net_sales": _money(net),
        "gross_profit": _money(gross),
        "margin_percent": _money((gross / net * 100) if net else Decimal("0")),
        "top_products": [
            {"name": r["n"], "quantity": r["q"], "revenue": _money(r["r"])}
            for r in ranked
        ],
    }


def _seed(app):
    tenant = TenantService().create_tenant(
        name="Aggregate Store", slug="aggregate-store", email="agg@test.com"
    )
    from core.utils import utc_now

    now = utc_now()
    for idx, status in enumerate(("paid", "paid", "awaiting")):
        order = Order(
            tenant_id=tenant.id,
            order_number=f"AGG-{idx}",
            status=status,
            payment_status=status,
            customer_email="buyer@test.com",
            shipping_address={},
            total=Decimal("100.00"),
            tax_amount=Decimal("5.00"),
            discount_amount=Decimal("2.00"),
            shipping_cost=Decimal("10.00"),
            created_at=now - timedelta(days=idx),
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(
            OrderItem(
                order_id=order.id,
                tenant_id=tenant.id,
                product_name=f"Product {idx}",
                unit_price=Decimal("10.00"),
                unit_cost=Decimal("2.50"),
                quantity=2,
                total_price=Decimal("30.00"),
            )
        )
    db.session.add(
        Product(
            tenant_id=tenant.id,
            name="Published",
            slug="published",
            price=Decimal("1.00"),
            is_published=True,
        )
    )
    db.session.add(
        Product(
            tenant_id=tenant.id,
            name="Draft",
            slug="draft",
            price=Decimal("2.00"),
            is_published=False,
        )
    )
    db.session.commit()
    return tenant.id, now


def test_sales_report_matches_legacy(app):
    with app.app_context():
        tenant_id, now = _seed(app)
        assert SalesReportService().build(tenant_id) == _legacy_report(tenant_id)
        assert SalesReportService().build(
            tenant_id, now - timedelta(days=1)
        ) == _legacy_report(tenant_id)


def test_sales_report_empty_tenant_shape(app):
    with app.app_context():
        result = SalesReportService().build(999999)
        assert result == _legacy_report(999999)
        assert result["orders_count"] == 0
        assert result["top_products"] == []
