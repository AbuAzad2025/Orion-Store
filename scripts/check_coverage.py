#!/usr/bin/env python3
"""Enforce per-file coverage from coverage_manifest.yaml (§0.8, §33.9 #8)."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "scripts" / "coverage_manifest.yaml"
COVERAGE_JSON = ROOT / "coverage.json"

SOURCE_ROOTS = ("02-CORE", "03-MODELS", "04-SERVICES", "05-API")


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _matches_any(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in patterns)


def _load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _min_for_file(rel: str, manifest: dict) -> float | None:
    files = manifest.get("files") or {}
    if rel in files:
        return float(files[rel]["min"])
    for prefix, default_min in (manifest.get("path_defaults") or {}).items():
        if rel.startswith(prefix):
            return float(default_min)
    return None


def _scan_source_files(exclude: list[str]) -> set[str]:
    found: set[str] = set()
    for root_name in SOURCE_ROOTS:
        root = ROOT / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            rel = _norm(path.relative_to(ROOT).as_posix())
            if _matches_any(rel, exclude):
                continue
            found.add(rel)
    return found


def _git_changed_files(base: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", f"{base}...HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [_norm(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def _coverage_percent(coverage_data: dict, rel: str) -> float | None:
    files = coverage_data.get("files") or {}
    for key, entry in files.items():
        if _norm(key) == rel:
            summary = entry.get("summary") or {}
            return float(summary.get("percent_covered", 0.0))
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check per-file coverage gates.")
    parser.add_argument(
        "--coverage-json",
        type=Path,
        default=COVERAGE_JSON,
        help="Path to coverage.json from pytest-cov",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Path to coverage_manifest.yaml",
    )
    parser.add_argument(
        "--diff-base",
        default="",
        help="Git ref for PR changed-files check (e.g. origin/main)",
    )
    args = parser.parse_args()

    if not args.coverage_json.is_file():
        print(
            f"ERROR: missing {args.coverage_json} — run pytest with --cov-report=json"
        )
        return 1

    manifest = _load_manifest(args.manifest)
    exclude = manifest.get("exclude_from_scan") or []
    manifest_files = manifest.get("files") or {}
    pr_modified_min = float(manifest.get("pr_modified_min", 80))

    with args.coverage_json.open(encoding="utf-8") as handle:
        coverage_data = json.load(handle)

    failures: list[str] = []
    rows: list[tuple[str, float, float, str]] = []

    for rel, spec in sorted(manifest_files.items()):
        minimum = float(spec["min"])
        actual = _coverage_percent(coverage_data, rel)
        if actual is None:
            failures.append(f"{rel}: not measured (add to pytest --cov paths)")
            continue
        wave = spec.get("wave", "?")
        rows.append((rel, actual, minimum, f"wave-{wave}"))
        if actual + 1e-9 < minimum:
            failures.append(f"{rel}: {actual:.1f}% < {minimum:.0f}% (wave-{wave})")

    scanned = _scan_source_files(exclude)
    manifest_keys = set(manifest_files.keys())
    untracked = sorted(scanned - manifest_keys)
    if untracked:
        for rel in untracked:
            failures.append(
                f"{rel}: not in coverage_manifest.yaml — register before merge"
            )

    if args.diff_base:
        for rel in _git_changed_files(args.diff_base):
            if not rel.endswith(".py"):
                continue
            if not any(rel.startswith(root) for root in SOURCE_ROOTS):
                continue
            if _matches_any(rel, exclude):
                continue
            if rel not in manifest_files:
                failures.append(
                    f"{rel}: modified in PR but missing from coverage_manifest.yaml"
                )
                continue
            actual = _coverage_percent(coverage_data, rel)
            if actual is None:
                failures.append(f"{rel}: modified in PR but not measured")
            elif actual + 1e-9 < pr_modified_min:
                failures.append(
                    f"{rel}: PR gate {actual:.1f}% < {pr_modified_min:.0f}%"
                )

    print("Coverage manifest check")
    print(f"{'File':<48} {'Actual':>7} {'Min':>5} {'Wave':>8}")
    print("-" * 72)
    for rel, actual, minimum, wave in rows:
        status = "OK" if actual + 1e-9 >= minimum else "FAIL"
        print(f"{rel:<48} {actual:6.1f}% {minimum:5.0f}% {wave:>8}  {status}")

    if untracked:
        print("\nUntracked source files (add to manifest):")
        for rel in untracked:
            print(f"  - {rel}")

    if failures:
        print("\nFAILURES:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print(f"\nOK — {len(rows)} manifest files meet their minimums.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
