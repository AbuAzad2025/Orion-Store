#!/usr/bin/env python3
"""Static RTL/WCAG audit of Orion templates and CSS.

Usage:
    python scripts/audit_a11y.py            # report
    python scripts/audit_a11y.py --check    # exit 1 when issues exist
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from jinja2 import Template, TemplateError

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIRS = (
    ROOT / "06-STOREFRONT" / "themes" / "default" / "templates",
    ROOT / "07-ADMIN" / "templates",
)

# Language → text direction. Storefront templates may compute these
# dynamically from `locale`, so the audit renders the <html> tag with
# representative locales instead of forcing the literal `ar`/`rtl`.
RTL_LOCALES = frozenset({"ar", "he"})
LTR_LOCALES = frozenset({"en", "fr"})
PROBE_LOCALES = ("ar", "en", "he", "fr")

_HTML_TAG_RE = re.compile(r"<html\b[^>]*>", re.I)
_HTML_ATTR_RE = re.compile(r"""\b(lang|dir)\s*=\s*["']([^"']*)["']""", re.I)


def _expected_direction(lang: str) -> str:
    code = lang[:2].lower()
    if code in RTL_LOCALES:
        return "rtl"
    if code in LTR_LOCALES:
        return "ltr"
    return ""


def _audit_html_tag(source: str, rel: str, issues: list[str]) -> None:
    tag_match = _HTML_TAG_RE.search(source)
    if not tag_match:
        return
    tag = tag_match.group(0)

    if "{{" in tag or "{%" in tag:
        try:
            variants = [
                Template(tag).render(locale=loc, lang=loc) for loc in PROBE_LOCALES
            ]
        except TemplateError as exc:
            issues.append(f"{rel}: cannot evaluate html lang/dir: {exc}")
            return
    else:
        variants = [tag]

    local_issues: list[str] = []
    for rendered in variants:
        attrs = {key.lower(): value for key, value in _HTML_ATTR_RE.findall(rendered)}
        lang = attrs.get("lang", "").strip()
        direction = attrs.get("dir", "").strip().lower()
        if not lang:
            local_issues.append(f"{rel}: html tag is missing lang")
            continue
        if not direction:
            local_issues.append(f"{rel}: html tag is missing dir")
            continue
        expected = _expected_direction(lang)
        if expected and direction != expected:
            local_issues.append(
                f'{rel}: html dir="{direction}" contradicts lang="{lang}" '
                f'(expected "{expected}")'
            )
    issues.extend(dict.fromkeys(local_issues))


def _templates():
    for directory in TEMPLATE_DIRS:
        if directory.is_dir():
            yield from directory.rglob("*.html")


def audit() -> list[str]:
    issues: list[str] = []
    for path in sorted(_templates()):
        rel = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")

        _audit_html_tag(source, rel, issues)

        for match in re.finditer(r"<img\b[^>]*>", source, re.I):
            if not re.search(r"\balt\s*=", match.group(0), re.I):
                issues.append(f"{rel}: <img> without alt")

        for match in re.finditer(r"<button\b[^>]*>(.*?)</button>", source, re.I | re.S):
            tag, body = match.group(0), match.group(1)
            if not re.search(r"\b(aria-label|title)\s*=", tag, re.I):
                text = re.sub(r"<[^>]+>", "", body).strip()
                if not text:
                    issues.append(f"{rel}: <button> without accessible name")

        for match in re.finditer(r"<input\b[^>]*>", source, re.I):
            tag = match.group(0)
            if re.search(r'\btype\s*=\s*["\'](hidden|submit|button)', tag, re.I):
                continue
            if not re.search(
                r"\b(aria-label|aria-labelledby|placeholder)\s*=", tag, re.I
            ):
                issues.append(f"{rel}: <input> without label/aria-label/placeholder")

    for directory in TEMPLATE_DIRS:
        if not directory.is_dir():
            issues.append(
                f"missing template directory: {directory.relative_to(ROOT).as_posix()}"
            )

    rtl_css = (
        ROOT / "06-STOREFRONT" / "themes" / "default" / "static" / "css" / "rtl.css"
    )
    if not rtl_css.is_file():
        issues.append("rtl.css is missing")
    elif re.search(
        r"(?:margin|padding)-(left|right)\s*:", rtl_css.read_text(encoding="utf-8")
    ):
        issues.append(
            "rtl.css: uses physical margin/padding-left/right instead of logical properties"
        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    issues = audit()
    print(f"a11y/RTL issues: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    return 1 if args.check and issues else 0


if __name__ == "__main__":
    sys.exit(main())
