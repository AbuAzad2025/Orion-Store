"""Tests for core.events."""

from __future__ import annotations

from core.events import clear_subscribers, publish, subscribe


def test_publish_dispatches_to_subscriber():
    clear_subscribers()
    received: list[str] = []

    def handler(**payload):
        received.append(payload.get("order_id"))

    subscribe("order.paid", handler)
    publish("order.paid", order_id="ord_123")
    assert received == ["ord_123"]
    clear_subscribers()
