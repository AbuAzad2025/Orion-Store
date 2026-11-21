"""Design tokens must meet WCAG AA contrast on Orion surfaces."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_design_tokens_meet_wcag_aa() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_contrast.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout
    assert "contrast violations: 0" in result.stdout
