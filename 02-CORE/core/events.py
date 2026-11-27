"""Domain event bus — publish/subscribe (§3.8)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

EventHandler = Callable[..., None]

_subscribers: dict[str, list[EventHandler]] = defaultdict(list)


def subscribe(event_name: str, handler: EventHandler) -> None:
    """Register a handler for a domain event."""
    _subscribers[event_name].append(handler)


def unsubscribe(event_name: str, handler: EventHandler) -> None:
    """Remove a handler."""
    if handler in _subscribers[event_name]:
        _subscribers[event_name].remove(handler)


def publish(event_name: str, **payload: Any) -> None:
    """Dispatch event to all subscribers, isolating handler failures.

    A failing notification/workflow subscriber must never turn an already
    committed payment into an HTTP 500; log it and continue.
    """
    import logging

    log = logging.getLogger(__name__)
    for handler in list(_subscribers[event_name]):
        try:
            handler(**payload)
        except Exception:
            log.exception("Event subscriber failed for %s", event_name)


def clear_subscribers() -> None:
    """Reset all handlers — for tests only."""
    _subscribers.clear()
