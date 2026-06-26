#!/usr/bin/env python3
"""Fail CI if any source file exceeds configured line limits (§0.3)."""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
}

DEFAULT_RULES: list[tuple[str, int]] = [
    ("**/*_service.py", 400),
    ("05-API/v1/*.py", 300),
    ("03-MODELS/**/*.py", 250),
    ("migrations/versions/*.py", 200),
]

DEFAULT_MAX = 500

SCAN_EXTENSIONS = {".py", ".js", ".html", ".j2", ".jinja2", ".css"}


def _max_for(path: Path) -> int:
    rel = path.relative_to(ROOT).as_posix()
    for pattern, limit in DEFAULT_RULES:
        if fnmatch.fnmatch(rel, pattern):
            return limit
    return DEFAULT_MAX


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in SCAN_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def main() -> int:
    violations: list[str] = []
    for path in _iter_files():
        limit = _max_for(path)
        line_count = len(
            path.read_text(encoding="utf-8", errors="replace").splitlines()
        )
        if line_count > limit:
            rel = path.relative_to(ROOT)
            violations.append(f"{rel}: {line_count} lines (max {limit})")

    if violations:
        print("File length violations (§0.3):", file=sys.stderr)
        for item in sorted(violations):
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("File length check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
