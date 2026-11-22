#!/usr/bin/env python3
"""Download free-stock product photos and attach them to every seeded tenant.

Images come from Unsplash's public CDN (free to use under the Unsplash
License). A single copy of each photo is downloaded, then placed into a
per-tenant asset folder so every storefront serves its own local files.

Usage:
  DATABASE_URL=postgresql://... FLASK_ENV=development python scripts/fetch_product_images.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
for part in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API", "06-STOREFRONT", "07-ADMIN"):
    sys.path.insert(0, str(ROOT / part))

ASSETS = ROOT / "06-STOREFRONT/themes/default/static/images/products"
TENANTS = ["outlet", "gulf", "euro", "atlantic", "sterling"]

# product slug -> Unsplash photo id (keyword-matched, free-stock).
PRODUCT_IMAGES = {
    "smart-phone-pro": "photo-1592890288564-76628a30a657",
    "wireless-headphones": "photo-1505740420928-5e560c06d30e",
    "winter-jacket": "photo-1706765779494-2705542ebe74",
    "sneakers": "photo-1542291026-7eec264c27ff",
    "desk-lamp": "photo-1519219788971-8d9797e0928e",
    "dinner-set": "photo-1631008788127-57317667a0d2",
    "woody-perfume": "photo-1523293182086-7651a899d37f",
    "moisturizer": "photo-1585945037805-5fd82c2e60b1",
    "yoga-mat": "photo-1599901860904-17e6ed7083a0",
    "adjustable-dumbbell": "photo-1784894645353-81486c66a687",
    "modern-business-guide": "photo-1512820790803-83ca734da794",
    "city-novel": "photo-1541963463532-d68292c34b19",
}


def fetch(url: str, dest: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 OrionDemo/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
    if len(data) < 5000:
        raise RuntimeError(f"suspiciously small image: {len(data)} bytes")
    dest.write_bytes(data)


def main() -> None:
    staging = pathlib.Path(tempfile.gettempdir()) / "orion_product_images"
    staging.mkdir(parents=True, exist_ok=True)

    print("Downloading product photos from Unsplash...")
    for slug, photo_id in PRODUCT_IMAGES.items():
        target = staging / f"{slug}.jpg"
        if not target.exists() or target.stat().st_size < 5000:
            url = f"https://images.unsplash.com/{photo_id}?w=800&q=75&fit=crop&fm=jpg"
            fetch(url, target)
        print(f"  {slug}.jpg  {target.stat().st_size // 1024} KB")

    for tenant in TENANTS:
        folder = ASSETS / tenant
        folder.mkdir(parents=True, exist_ok=True)
        for slug in PRODUCT_IMAGES:
            shutil.copyfile(staging / f"{slug}.jpg", folder / f"{slug}.jpg")

    # Attach the local URL to every product across all tenants. Import the
    # app factory first so extensions are initialised before any models.
    from orion.app import create_app
    from orion.extensions import db

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        from catalog.product import Product
        from tenant.tenant import Tenant

        slugs = {t.slug: t.id for t in Tenant.query.all()}
        updated = 0
        for tenant_slug, tenant_id in slugs.items():
            if tenant_slug not in TENANTS:
                continue
            for product in Product.query.filter_by(tenant_id=tenant_id).all():
                if product.slug in PRODUCT_IMAGES:
                    product.image_url = (
                        f"/store/static/images/products/{tenant_slug}/{product.slug}.jpg"
                    )
                    updated += 1
        db.session.commit()
        print(f"Attached images to {updated} products across {len(TENANTS)} tenants.")


if __name__ == "__main__":
    main()
