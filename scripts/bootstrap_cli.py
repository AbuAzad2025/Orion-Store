#!/usr/bin/env python3
"""Secure CLI bootstrap for the first platform administrator.

Usage:

    python scripts/bootstrap_cli.py

This script is the **only** approved path for creating the first platform
administrator. It:

* Refuses to run when any platform administrator already exists.
* Prompts the operator for email and password (hidden input).
* Requires a minimum password length of 8 characters.
* Seeds default platform settings before creating the admin.
* Exits with code 1 on any error.

It must **never** be exposed through an HTTP endpoint or automated deployment
pipeline without human operator confirmation.
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap PATH — resolve project root dynamically
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _sub in (
    "02-CORE",
    "03-MODELS",
    "04-SERVICES",
    "05-API",
    "06-STOREFRONT",
    "07-ADMIN",
):
    _p = str(_PROJECT_ROOT / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "development")

    # The app factory must be imported and run before any model/service import.
    # Otherwise `tenant.tenant` is partially initialised while the app factory
    # loads `core.middleware`, causing a circular import.
    from orion.app import create_app

    app = create_app()

    from auth.auth_service import AuthService
    from platform_svc.platform_settings_service import PlatformSettingsService
    from user.user import User

    with app.app_context():
        # ── check for ANY existing platform admin ──────────────────────
        existing = User.query.filter(
            User.tenant_id.is_(None),
            User.is_superuser.is_(True),
            User.deleted_at.is_(None),
        ).first()
        if existing is not None:
            msg = (
                f"ERROR: A platform administrator already exists "
                f"(email={existing.email!r}). "
                f"Bootstrap is blocked. Use the existing account or contact "
                f"an existing platform administrator."
            )
            print(msg, file=sys.stderr)
            sys.exit(1)

        # ── explicit operator input ────────────────────────────────────
        email = input("Platform admin email: ").strip().lower()
        if not email:
            print("ERROR: Email cannot be empty.", file=sys.stderr)
            sys.exit(1)

        password = getpass.getpass("Password (min 8 chars): ")
        if len(password) < 8:
            print("ERROR: Password must be at least 8 characters.", file=sys.stderr)
            sys.exit(1)

        # ── seed + create ──────────────────────────────────────────────
        PlatformSettingsService().ensure_seeded()
        auth = AuthService()
        user = auth.register_super_admin(
            email=email, password=password, first_name="Platform"
        )
        print(f"SUCCESS: Platform admin created with email: {user.email}")


if __name__ == "__main__":
    main()
