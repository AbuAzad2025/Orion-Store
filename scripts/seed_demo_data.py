#!/usr/bin/env python3
"""Seed a rich, idempotent demo dataset for functional/accounting testing.

Usage:
  DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/seed_demo_data.py

Creates (per tenant): 6 categories, 12 products, 2 warehouses with stock,
4 customers + 1 admin, 5 paid COD orders with invoices, one partial refund,
store credit, a voucher, a gift registry and a BOPIS location. Real FX rates
are fetched for every tenant currency. Existing tenants are skipped.
"""

from __future__ import annotations

import os
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
for part in (
    "02-CORE",
    "03-MODELS",
    "04-SERVICES",
    "05-API",
    "06-STOREFRONT",
    "07-ADMIN",
):
    sys.path.insert(0, str(ROOT / part))

from orion.app import create_app
from orion.extensions import db

TENANTS = [
    ("National Outlet", "outlet", "ILS", "0562000001", "+972562000001"),
    ("Gulf Trading", "gulf", "AED", "+971500000001", "+971500000001"),
    ("Euro Select", "euro", "EUR", "+33123456789", "+33123456789"),
    ("Atlantic Goods", "atlantic", "USD", "+12125550101", "+12125550101"),
    ("Sterling House", "sterling", "GBP", "+442079460101", "+442079460101"),
]

CATEGORIES = [
    (
        "electronics",
        "إلكترونيات",
        [
            ("هاتف ذكي برو", "smart-phone-pro", "1899.00", "1499"),
            ("سماعات لاسلكية", "wireless-headphones", "349.00", "249"),
        ],
    ),
    (
        "fashion",
        "أزياء",
        [
            ("جاكيت شتوي", "winter-jacket", "299.00", "219"),
            ("حذاء رياضي", "sneakers", "219.00", "159"),
        ],
    ),
    (
        "home",
        "المنزل",
        [
            ("مصباح مكتبي", "desk-lamp", "159.00", "119"),
            ("طقم أطباق", "dinner-set", "279.00", "199"),
        ],
    ),
    (
        "beauty",
        "الجمال",
        [
            ("عطر خشبي", "woody-perfume", "389.00", "299"),
            ("كريم مرطب", "moisturizer", "129.00", "99"),
        ],
    ),
    (
        "sports",
        "الرياضة",
        [
            ("حصيرة يوغا", "yoga-mat", "139.00", "99"),
            ("دمبل قابل للتعديل", "adjustable-dumbbell", "459.00", "349"),
        ],
    ),
    (
        "books",
        "الكتب",
        [
            ("دليل الأعمال الحديث", "modern-business-guide", "89.00", "69"),
            ("رواية المدينة", "city-novel", "69.00", "49"),
        ],
    ),
]


def main() -> None:
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        from bopis_svc.bopis_service import BopisService
        from currency_svc.currency_service import CurrencyService
        from discount_svc.voucher_service import VoucherService
        from feature_flag.feature_flag import FeatureFlag
        from gift_svc.gift_registry_service import GiftRegistryService
        from store_credit_svc.store_credit_service import StoreCreditService

        from auth.auth_service import AuthService
        from catalog_svc.category_service import CategoryService
        from catalog_svc.product_service import ProductService
        from oms_svc.oms_service import OmsService
        from order_svc.cart_service import CartService
        from order_svc.checkout_service import CheckoutService
        from payment_svc.payment_service import PaymentService
        from tenant.tenant import Tenant
        from tenant_svc.tenant_service import TenantService
        from user.user import User

        # Make the language switcher work in the demo dataset.
        multi_language = FeatureFlag.query.filter_by(code="multi_language").first()
        if multi_language:
            multi_language.default_value = True
            db.session.commit()

        if not User.query.filter_by(email="root@azadexa.test", tenant_id=None).first():
            auth_register = AuthService()
            auth_register.register_super_admin(
                email="root@azadexa.test",
                password="password123",  # nosec B106
                first_name="منصة",
            )

        auth = AuthService()
        categories = CategoryService()
        products = ProductService()
        oms = OmsService()
        carts = CartService()
        checkout = CheckoutService()
        payments = PaymentService()
        credit = StoreCreditService()
        vouchers = VoucherService()
        gifts = GiftRegistryService()

        # Real FX rates for all demo currencies, persisted for offline fallback.
        fx = CurrencyService()
        for _n, _s, currency, _p, _pi in TENANTS:
            fx.refresh_live_rate("ILS", currency)
        print("FX rates refreshed")

        for name, slug, currency, phone, intl in TENANTS:
            if Tenant.query.filter_by(slug=slug).first():
                print("skip existing tenant", slug)
                continue
            tenant = TenantService().create_tenant(
                name=name, slug=slug, email=f"info@{slug}.test", status="active"
            )
            tenant.default_currency = currency
            tenant.country_code = (
                "PS"
                if currency == "ILS"
                else (
                    "AE"
                    if currency == "AED"
                    else (
                        "US"
                        if currency == "USD"
                        else ("GB" if currency == "GBP" else "FR")
                    )
                )
            )
            tenant.phone = phone
            db.session.commit()

            wh1 = oms.create_warehouse(
                tenant_id=tenant.id,
                name="المستودع الرئيسي",
                code="main",
                is_default=True,
                address={"city": "المركز"},
            )
            wh2 = oms.create_warehouse(
                tenant_id=tenant.id,
                name="مستودع التخزين",
                code="overflow",
                address={"city": "الضاحية"},
            )
            location = BopisService().create_location(
                tenant_id=tenant.id,
                code="pickup",
                name="نقطة الاستلام",
                address={"text": "الفرع الرئيسي"},
                warehouse_id=wh1.id,
                phone=phone,
            )
            BopisService().create_slot(
                tenant_id=tenant.id,
                location_id=location.id,
                day_of_week=0,
                start_time="09:00",
                end_time="18:00",
                max_orders=20,
            )

            admin = auth.register_tenant_user(
                tenant_id=tenant.id,
                email=f"admin@{slug}.test",
                password="password123",  # nosec B106
                is_admin=True,
            )
            customers = [
                auth.register_tenant_user(
                    tenant_id=tenant.id,
                    email=f"buyer{i}@{slug}.test",
                    password="password123",  # nosec B106
                    is_admin=False,
                )
                for i in range(1, 5)
            ]

            cat_ids = {}
            for cat_slug, cat_name, items in CATEGORIES:
                cat = categories.create(
                    tenant_id=tenant.id, name=cat_name, slug=cat_slug
                )
                cat_ids[cat_slug] = cat.id
                for p_name, p_slug, price, old in items:
                    products.create(
                        tenant_id=tenant.id,
                        name=p_name,
                        slug=p_slug,
                        price=price,
                        sku=f"{slug}-{p_slug}".upper(),
                        quantity=40,
                        category_id=cat.id,
                        is_published=True,
                        is_featured=(p_slug == "smart-phone-pro"),
                        short_description=f"{p_name} — جودة عالية وسعر مناسب",
                        description=f"وصف تفصيلي لمنتج {p_name} ضمن فئة {cat_name}.",
                        compare_at_price=old,
                        image_url=None,  # images must be uploaded into PRODUCT_IMAGES_DIR
                    )

            # Inventory in both warehouses.
            from catalog.product import Product

            for product in Product.query.filter_by(tenant_id=tenant.id).all():
                oms.upsert_inventory(
                    tenant_id=tenant.id,
                    warehouse_id=wh1.id,
                    product_id=product.id,
                    quantity=30,
                )
                oms.upsert_inventory(
                    tenant_id=tenant.id,
                    warehouse_id=wh2.id,
                    product_id=product.id,
                    quantity=10,
                )

            vouchers.create(
                tenant_id=tenant.id,
                code=f"WELCOME-{slug[:3].upper()}",
                name="خصم ترحيبي",
                type="percentage",
                value="10",
                usage_limit=100,
            )
            credit.add_funds(
                tenant_id=tenant.id,
                customer_email=customers[0].email,
                amount="250",
                reason="رصيد ترحيبي",
            )
            registry = gifts.create_registry(
                tenant_id=tenant.id,
                customer_email=customers[1].email,
                registry_name=f"قائمة {name}",
                is_public=True,
                user_id=customers[1].id,
            )
            first_product = Product.query.filter_by(tenant_id=tenant.id).first()
            gifts.add_item(
                tenant_id=tenant.id,
                registry_id=registry.id,
                product_id=first_product.id,
                quantity=2,
            )

            order_ids = []
            all_products = Product.query.filter_by(tenant_id=tenant.id).all()
            for i, customer in enumerate(customers):
                for n in range(2):
                    cart = carts.get_or_create_cart(tenant_id=tenant.id)
                    chosen = all_products[(i * 2 + n) % len(all_products)]
                    carts.add_item(cart=cart, product_id=chosen.id, quantity=(n + 1))
                    order = checkout.checkout(
                        cart=cart,
                        customer_email=customer.email,
                        user_id=customer.id,
                        is_guest=False,
                        shipping_address={
                            "city": "المركز",
                            "country_code": tenant.country_code,
                        },
                    )
                    payments.pay_order(
                        tenant_id=tenant.id,
                        order_public_id=str(order.public_id),
                        payment_method="cod",
                    )
                    order_ids.append(order.id)

            # Partial refund on one paid order per tenant.
            from payment.payment import Payment

            paid = Payment.query.filter_by(
                tenant_id=tenant.id, status="completed"
            ).first()
            if paid:
                try:
                    payments.refund(
                        tenant_id=tenant.id,
                        payment_public_id=str(paid.public_id),
                        amount="10.00",
                        reason="استرداد جزئي تجريبي",
                    )
                except Exception as exc:  # noqa: BLE001 - demo data best effort
                    print("refund skipped", slug, exc)

            print(
                f"seeded {slug}: 12 products, 2 warehouses, 4 customers, "
                f"{len(order_ids)} paid orders, credit/voucher/registry"
            )

        print("DEMO SEED COMPLETE")


if __name__ == "__main__":
    main()
