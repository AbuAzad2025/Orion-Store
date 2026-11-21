"""Every tenant-scoped table must have an RLS policy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_all_tenant_tables_have_rls() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_rls.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout
    assert "missing RLS           : 0" in result.stdout
