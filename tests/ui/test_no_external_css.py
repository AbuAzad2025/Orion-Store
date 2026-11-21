"""No runtime CDN dependency: Tailwind is built and served locally."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIRS = (
    ROOT / "06-STOREFRONT" / "themes" / "default" / "templates",
    ROOT / "07-ADMIN" / "templates",
)
CSS_FILES = (
    ROOT / "06-STOREFRONT" / "themes" / "default" / "static" / "css" / "tailwind.css",
    ROOT / "07-ADMIN" / "static" / "css" / "tailwind.css",
)


def test_no_cdn_references_in_templates() -> None:
    offenders: list[str] = []
    for directory in TEMPLATE_DIRS:
        for template in directory.rglob("*.html"):
            if "cdn.tailwindcss.com" in template.read_text(encoding="utf-8"):
                offenders.append(str(template.relative_to(ROOT)))
    assert offenders == [], f"CDN references remain: {offenders}"


def test_local_tailwind_build_exists() -> None:
    for css in CSS_FILES:
        assert css.is_file(), f"Missing local CSS build: {css}"
        assert css.stat().st_size > 1000, f"CSS build looks empty: {css}"


def test_csp_does_not_allow_cdn(app) -> None:
    with app.test_client() as client:
        response = client.get("/health")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "cdn.tailwindcss.com" not in csp
        assert "'self'" in csp
