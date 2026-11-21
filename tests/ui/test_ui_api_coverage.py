"""Every static API reference in the UI must resolve to a registered route."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ui_api_references_are_valid() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_ui_coverage.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout
    assert "broken references     : 0" in result.stdout
