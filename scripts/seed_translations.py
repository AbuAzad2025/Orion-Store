#!/usr/bin/env python3
"""Seed English translations for the demo catalogue (idempotent).

Usage:
  DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/seed_translations.py
"""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
for part in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API", "06-STOREFRONT", "07-ADMIN"):
    sys.path.insert(0, str(ROOT / part))

PRODUCTS = {
    "smart-phone-pro": "Pro Smartphone",
    "wireless-headphones": "Wireless Headphones",
    "winter-jacket": "Winter Jacket",
    "sneakers": "Sneakers",
    "desk-lamp": "Desk Lamp",
    "dinner-set": "Dinner Set",
    "woody-perfume": "Woody Perfume",
    "moisturizer": "Moisturizer",
    "yoga-mat": "Yoga Mat",
    "adjustable-dumbbell": "Adjustable Dumbbell",
    "modern-business-guide": "Modern Business Guide",
    "city-novel": "City Novel",
}

CATEGORIES = {
    "electronics": "Electronics",
    "fashion": "Fashion",
    "home": "Home",
    "beauty": "Beauty",
    "sports": "Sports",
    "books": "Books",
}

DESCRIPTIONS = {
    slug: f"{name} — premium quality at a fair price."
    for slug, name in PRODUCTS.items()
}


def main() -> None:
    from orion.app import create_app
    from orion.extensions import db

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        from catalog.category import Category
        from catalog.product import Product
        from i18n.category_translation import CategoryTranslation
        from i18n.product_translation import ProductTranslation

        created = 0
        for product in Product.query.all():
            name = PRODUCTS.get(product.slug)
            if not name:
                continue
            row = ProductTranslation.query.filter_by(
                product_id=product.id, locale="en"
            ).first()
            if row is None:
                row = ProductTranslation(
                    tenant_id=product.tenant_id,
                    product_id=product.id,
                    locale="en",
                )
                db.session.add(row)
                created += 1
            row.name = name
            row.slug = product.slug
            row.description = DESCRIPTIONS[product.slug]

        for category in Category.query.all():
            name = CATEGORIES.get(category.slug)
            if not name:
                continue
            row = CategoryTranslation.query.filter_by(
                category_id=category.id, locale="en"
            ).first()
            if row is None:
                row = CategoryTranslation(
                    tenant_id=category.tenant_id,
                    category_id=category.id,
                    locale="en",
                )
                db.session.add(row)
                created += 1
            row.name = name
            row.slug = category.slug
            row.description = f"Browse our {name.lower()} collection."

        db.session.commit()
        print(f"seeded {created} translation rows")


if __name__ == "__main__":
    main()
