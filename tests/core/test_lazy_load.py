"""Lazy-load attribute helpers."""

from __future__ import annotations

from core.lazy_load import lazy_image_attrs


def test_lazy_image_attrs_deferred():
    attrs = lazy_image_attrs("https://cdn.example/img.jpg", alt="Widget")
    assert attrs["data-lazy-src"] == "https://cdn.example/img.jpg"
    assert attrs["loading"] == "lazy"
    assert "src" not in attrs


def test_lazy_image_attrs_high_priority():
    attrs = lazy_image_attrs(
        "https://cdn.example/hero.jpg", alt="Hero", high_priority=True
    )
    assert attrs["src"] == "https://cdn.example/hero.jpg"
    assert "data-lazy-src" not in attrs
