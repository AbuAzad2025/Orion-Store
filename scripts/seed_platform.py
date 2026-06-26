#!/usr/bin/env python3
"""Seed platform_settings singleton (wave 2 #20)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API"):
    p = str(ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from orion.app import create_app  # noqa: E402
from platform_svc.platform_settings_service import PlatformSettingsService  # noqa: E402


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "development")
    app = create_app()
    with app.app_context():
        row = PlatformSettingsService().ensure_seeded()
        print(f"Seeded platform_settings: {row.platform_name} ({row.owner_name})")


if __name__ == "__main__":
    main()
