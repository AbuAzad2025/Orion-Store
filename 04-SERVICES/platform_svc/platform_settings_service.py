"""Platform settings service (wave 2 #20)."""

from __future__ import annotations

from decimal import Decimal

from core.exceptions import NotFoundError
from orion.extensions import db
from platform_models.platform_settings import PlatformSettings


class PlatformSettingsService:
    def get_singleton(self) -> PlatformSettings:
        row = PlatformSettings.query.filter_by(singleton="1").first()
        if not row:
            raise NotFoundError("Platform settings not seeded.")
        return row

    def ensure_seeded(self) -> PlatformSettings:
        existing = PlatformSettings.query.filter_by(singleton="1").first()
        if existing:
            return existing
        row = PlatformSettings(
            platform_name="Azadexa",
            footer_html=(
                '<footer id="azadexa-platform-footer" '
                'class="azadexa-platform-footer" data-immutable="true">'
                "Powered by Azadexa &mdash; Ahmad Ghannam</footer>"
            ),
            owner_name="Ahmad Ghannam",
            owner_phone="0562150193",
            owner_phone_intl="+972562150193",
            default_commission_percent=Decimal("0.0100"),
            singleton="1",
            valuepayment_enabled=True,
            valuepayment_config={},
        )
        db.session.add(row)
        db.session.commit()
        return row
