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
    """Dispatch event to all subscribers (sync — wave 0)."""
    for handler in list(_subscribers[event_name]):
        handler(**payload)


def clear_subscribers() -> None:
    """Reset all handlers — for tests only."""
    _subscribers.clear()
