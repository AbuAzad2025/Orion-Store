#!/usr/bin/env python3
"""Pre-launch environment and health verification (§18)."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

REQUIRED = ("SECRET_KEY", "ENCRYPTION_KEY", "DATABASE_URL")
RECOMMENDED = ("REDIS_URL", "JWT_SECRET_KEY", "SMTP_HOST")


def main() -> int:
    missing = [key for key in REQUIRED if not os.environ.get(key)]
    if missing:
        print("MISSING required:", ", ".join(missing))
        return 1
    for key in RECOMMENDED:
        if not os.environ.get(key):
            print(f"WARN: {key} not set")
    base = os.environ.get("LAUNCH_VERIFY_URL", "http://127.0.0.1:5000")
    for path in ("/health", "/ready"):
        url = f"{base.rstrip('/')}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status >= 400:
                    print(f"FAIL {url} status={resp.status}")
                    return 1
                print(f"OK {url}")
        except urllib.error.URLError as exc:
            print(f"FAIL {url}: {exc}")
            return 1
    print("Launch verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
