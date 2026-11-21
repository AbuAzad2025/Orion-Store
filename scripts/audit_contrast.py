#!/usr/bin/env python3
"""Check WCAG AA contrast for the Orion design tokens.

Usage:
    python scripts/audit_contrast.py
    python scripts/audit_contrast.py --check   # exit 1 on any AA violation
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "01-FOUNDATION" / "assets" / "orion-theme.css"

PAIRS = (
    ("--orion-text", "--orion-bg"),
    ("--orion-text", "--orion-panel"),
    ("--orion-muted", "--orion-bg"),
    ("--orion-muted", "--orion-panel"),
    ("--orion-gold", "--orion-bg"),
    ("--orion-gold", "--orion-panel"),
    ("--orion-accent", "--orion-bg"),
    ("--orion-danger", "--orion-panel"),
    ("--orion-success", "--orion-panel"),
)


def _tokens() -> dict[str, str]:
    source = THEME.read_text(encoding="utf-8")
    return dict(re.findall(r"(--orion-[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", source))


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _ratio(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    high, low = max(la, lb), min(la, lb)
    return (high + 0.05) / (low + 0.05)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    tokens = _tokens()
    violations: list[str] = []
    for foreground, background in PAIRS:
        if foreground not in tokens or background not in tokens:
            violations.append(f"missing token {foreground} or {background}")
            continue
        ratio = _ratio(tokens[foreground], tokens[background])
        status = "OK" if ratio >= 4.5 else "LOW"
        print(f"{status:3} {foreground} on {background}: {ratio:.2f}:1")
        if ratio < 4.5:
            violations.append(f"{foreground} on {background}: {ratio:.2f}:1")

    # Gold button label (#1b1405) on gold background.
    gold = tokens.get("--orion-gold", "#000000")
    ratio = _ratio("#1b1405", gold)
    print(f"{'OK' if ratio >= 4.5 else 'LOW':3} gold button label on --orion-gold: {ratio:.2f}:1")
    if ratio < 4.5:
        violations.append(f"gold button label: {ratio:.2f}:1")

    print(f"contrast violations: {len(violations)}")
    for item in violations:
        print(f"  - {item}")
    return 1 if args.check and violations else 0


if __name__ == "__main__":
    sys.exit(main())
