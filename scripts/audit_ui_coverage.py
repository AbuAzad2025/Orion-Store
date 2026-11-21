#!/usr/bin/env python3
"""Audit UI → backend API references.

Extracts API paths called from admin (``OrionAPI``) and storefront
(``StoreAPI.request``) JavaScript and verifies they exist in the Flask URL map.

Usage:
    python scripts/audit_ui_coverage.py
    python scripts/audit_ui_coverage.py --check   # exit 1 on broken references
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for part in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API", "06-STOREFRONT", "07-ADMIN"):
    path = str(ROOT / part)
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENCRYPTION_KEY", "ui-coverage-audit")
os.environ.setdefault("USE_SQLITE_TESTS", "1")

_ADMIN_CALL = re.compile(r"OrionAPI\.(?:get|post|put|delete)\(\s*[\"'`]([^\"'`]+)")
_STORE_CALL = re.compile(r"this\.request\(\s*[\"'`](?:GET|POST|PUT|DELETE)[\"'`]\s*,\s*[\"'`]([^\"'`]+)")
_PARAM = re.compile(r"<[^>]+>")


def _known_rules() -> set[str]:
    from orion.app import create_app

    app = create_app("testing")
    return {
        _PARAM.sub("{}", rule.rule).rstrip("/") or "/"
        for rule in app.url_map.iter_rules()
    }


def _matches(path: str, rules: set[str]) -> bool:
    path = path.rstrip("/") or "/"
    if path in rules:
        return True
    parts = path.strip("/").split("/")
    for rule in rules:
        rule_parts = rule.strip("/").split("/")
        if len(parts) != len(rule_parts):
            continue
        if all(r == p or r == "{}" for r, p in zip(rule_parts, parts)):
            return True
    return False


def audit() -> tuple[list[str], int]:
    rules = _known_rules()
    broken: list[str] = []
    checked = 0

    sources: list[tuple[Path, re.Pattern[str], str]] = []
    for js in sorted((ROOT / "07-ADMIN" / "static" / "js").glob("*.js")):
        sources.append((js, _ADMIN_CALL, "/api/v1"))
    for template in sorted((ROOT / "07-ADMIN" / "templates").rglob("*.html")):
        sources.append((template, _ADMIN_CALL, "/api/v1"))
    store_js = ROOT / "06-STOREFRONT" / "themes" / "default" / "static" / "js" / "store_api.js"
    if not store_js.is_file():
        broken.append("missing storefront API client: store_api.js")
    else:
        sources.append((store_js, _STORE_CALL, "/api/v1/store"))

    for path, pattern, prefix in sources:
        source = path.read_text(encoding="utf-8")
        for match in pattern.finditer(source):
            raw = match.group(1).split("?", 1)[0]
            if "${" in raw:
                continue  # dynamic path — checked at runtime by E2E
            full = f"{prefix}/{raw.lstrip('/')}"
            checked += 1
            if not _matches(full, rules):
                broken.append(f"{path.relative_to(ROOT).as_posix()}: {full}")
    return sorted(set(broken)), checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    broken, checked = audit()
    print(f"API references checked: {checked}")
    print(f"broken references     : {len(broken)}")
    for item in broken:
        print(f"  - {item}")
    return 1 if args.check and broken else 0


if __name__ == "__main__":
    sys.exit(main())
