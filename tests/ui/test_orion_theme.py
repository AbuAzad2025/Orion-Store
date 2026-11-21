"""Luxury theme wiring and static RTL/WCAG audit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BASE_TEMPLATES = (
    ROOT / "06-STOREFRONT" / "themes" / "default" / "templates" / "base.html",
    ROOT / "07-ADMIN" / "templates" / "admin_base.html",
    ROOT / "07-ADMIN" / "templates" / "admin_login.html",
    ROOT / "07-ADMIN" / "templates" / "store_financial_report.html",
)
THEME_FILES = (
    ROOT
    / "06-STOREFRONT"
    / "themes"
    / "default"
    / "static"
    / "css"
    / "orion-theme.css",
    ROOT / "07-ADMIN" / "static" / "css" / "orion-theme.css",
)


def test_theme_build_exists() -> None:
    for css in THEME_FILES:
        assert css.is_file()
        text = css.read_text(encoding="utf-8")
        assert "--orion-gold" in text
        assert ":focus-visible" in text
        assert "inset-inline-start" in text


def test_base_templates_use_local_theme() -> None:
    for template in BASE_TEMPLATES:
        text = template.read_text(encoding="utf-8")
        assert "orion-theme.css" in text, f"{template} does not load the theme"
        assert "orion-surface" in text, f"{template} has no luxury surface"


def test_a11y_audit_is_clean() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_a11y.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout
    assert "a11y/RTL issues: 0" in result.stdout
