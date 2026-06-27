"""List API pagination helpers (§0.6)."""

from __future__ import annotations

from typing import Any, TypeVar

from flask import request

MAX_PER_PAGE = 100
DEFAULT_PER_PAGE = 20

T = TypeVar("T")


def pagination_params() -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(
            MAX_PER_PAGE, max(1, int(request.args.get("per_page", DEFAULT_PER_PAGE)))
        )
    except (TypeError, ValueError):
        page, per_page = 1, DEFAULT_PER_PAGE
    return page, per_page


def paginate_query(
    query: Any, page: int, per_page: int
) -> tuple[list[Any], dict[str, int]]:
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, (total + per_page - 1) // per_page) if total else 1
    return items, {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
    }


def paginated_payload(
    key: str, items: list[T], meta: dict[str, int], serializer
) -> dict[str, Any]:
    return {key: [serializer(item) for item in items], "pagination": meta}
