"""Shared storefront catalog SQL pagination + clean-URL pager links."""

from __future__ import annotations

from typing import Any, Callable

from flask import request, url_for

from core.pagination import pagination_params

CATALOG_PER_PAGE = 12
_KEEP = (
    "q",
    "category",
    "featured",
    "price_min",
    "price_max",
    "sort",
    "locale",
    "currency",
)


def paginate_catalog(
    query: Any,
    *,
    endpoint: str,
    url_values: dict[str, Any] | None = None,
) -> tuple[list[Any], int, int, Callable[[int], str]]:
    """Apply SQL OFFSET/LIMIT paging and build canonical (clean) page URLs."""
    page, per_page = pagination_params()
    per_page = min(per_page, CATALOG_PER_PAGE)
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(page, 1), pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    def page_url(number: int) -> str:
        args = {k: v for k, v in request.args.items() if k in _KEEP}
        args["page"] = str(number)
        values = dict(url_values or {})
        values.update(args)
        return url_for(endpoint, **values)

    return items, page, pages, page_url
