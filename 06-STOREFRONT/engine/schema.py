"""Structured-data helpers for storefront pages."""

from __future__ import annotations

from core.store_token import signed_url

LOCAL_IMAGE_PREFIX = "/store/static/images/products/"


def product_schema(product, product_i18n: dict, tenant, store_token: str) -> dict:
    """Build Product JSON-LD with a freshly signed image URL."""
    local = product.image_url or ""
    image = (
        signed_url(local, store_token)
        if local.startswith(LOCAL_IMAGE_PREFIX)
        else local
    )
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product_i18n.get("name") or product.name,
        "image": ([image] if image else []),
        "offers": {
            "@type": "Offer",
            "price": str(product_i18n.get("price") or product.price),
            "priceCurrency": (tenant.default_currency or "ILS"),
            "availability": (
                "https://schema.org/InStock"
                if product.quantity > 0
                else "https://schema.org/OutOfStock"
            ),
        },
    }
