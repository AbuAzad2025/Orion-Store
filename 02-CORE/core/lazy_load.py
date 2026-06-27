"""Lazy-load helpers for storefront media (§18, phase 14)."""

from __future__ import annotations


def lazy_image_attrs(
    src: str,
    *,
    alt: str = "",
    high_priority: bool = False,
) -> dict[str, str]:
    """Return HTML attributes for deferred image loading."""
    if high_priority:
        return {"src": src, "alt": alt}
    return {
        "data-lazy-src": src,
        "alt": alt,
        "loading": "lazy",
        "decoding": "async",
    }
