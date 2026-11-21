#!/usr/bin/env python3
"""Fail CI if any source file exceeds the limits in pyproject.toml (§0.3).

All limits live in ``[tool.orion.file_length]``. This script deliberately has
no hard-coded per-path exceptions: an exception must be declared (and justified)
in pyproject.toml, otherwise it silently weakens the gate.
"""

from __future__ import annotations

import fnmatch
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
}

SCAN_EXTENSIONS = {".py", ".js", ".html", ".j2", ".jinja2", ".css"}


def _load_config(path: Path | None = None) -> dict:
    """Read ``[tool.orion.file_length]`` — the single source of truth."""
    with (path or PYPROJECT).open("rb") as handle:
        data = tomllib.load(handle)
    return (data.get("tool") or {}).get("orion", {}).get("file_length") or {}


def _max_for(rel: str, config: dict) -> int:
    for entry in config.get("paths", []):
        if fnmatch.fnmatch(rel, entry["glob"]):
            return int(entry["max"])
    return int(config.get("default_max", 500))


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
    config = _load_config()
    if "default_max" not in config or "paths" not in config:
        print(
            f"ERROR: [tool.orion.file_length] is missing or incomplete in {PYPROJECT}",
            file=sys.stderr,
        )
        return 1

    violations: list[str] = []
    for path in _iter_files():
        rel = path.relative_to(ROOT).as_posix()
        limit = _max_for(rel, config)
        line_count = len(
            path.read_text(encoding="utf-8", errors="replace").splitlines()
        )
        if line_count > limit:
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
