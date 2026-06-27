#!/usr/bin/env python3
"""Seed closed-beta demo stores (§18 — 10 tenants Palestine/Jordan)."""

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

BETA_STORES: list[tuple[str, str, str]] = [
    ("متجر رام الله", "beta-ramallah", "ramallah@beta.azadexa.com"),
    ("متجر نابلس", "beta-nablus", "nablus@beta.azadexa.com"),
    ("متجر الخليل", "beta-hebron", "hebron@beta.azadexa.com"),
    ("متجر جنين", "beta-jenin", "jenin@beta.azadexa.com"),
    ("متجر بيت لحم", "beta-bethlehem", "bethlehem@beta.azadexa.com"),
    ("متجر طولكرم", "beta-tulkarm", "tulkarm@beta.azadexa.com"),
    ("متجر عمان", "beta-amman", "amman@beta.azadexa.com"),
    ("متجر إربد", "beta-irbid", "irbid@beta.azadexa.com"),
    ("متجر الزرقاء", "beta-zarqa", "zarqa@beta.azadexa.com"),
    ("متجر العقبة", "beta-aqaba", "aqaba@beta.azadexa.com"),
]
DEFAULT_ADMIN_PASSWORD = "BetaStore2026!"


def main() -> None:
    from auth.auth_service import AuthService
    from platform_svc.platform_settings_service import PlatformSettingsService
    from tenant.tenant import Tenant
    from tenant_svc.tenant_service import TenantService

    os.environ.setdefault("FLASK_ENV", "development")
    app = create_app()
    slugs: list[str] = []
    with app.app_context():
        PlatformSettingsService().ensure_seeded()
        tenants = TenantService()
        auth = AuthService()
        for name, slug, email in BETA_STORES:
            existing = Tenant.query.filter_by(slug=slug, deleted_at=None).first()
            if existing:
                slugs.append(slug)
                continue
            tenant = tenants.create_tenant(name=name, slug=slug, email=email)
            auth.register_tenant_user(
                tenant_id=tenant.id,
                email=email,
                password=DEFAULT_ADMIN_PASSWORD,
                is_admin=True,
            )
            slugs.append(slug)
            print(f"Seeded beta tenant: {slug} ({name})")
    print("BETA_TENANT_SLUGS=" + ",".join(slugs))


if __name__ == "__main__":
    main()
