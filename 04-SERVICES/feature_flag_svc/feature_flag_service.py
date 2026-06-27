"""Feature flag seeding and tenant overrides (wave 7 #61)."""

from __future__ import annotations

from feature_flag.feature_flag import FeatureFlag
from feature_flag.feature_flag_override import FeatureFlagOverride

from core.exceptions import NotFoundError
from orion.extensions import db


class FeatureFlagService:
    MVP_FLAGS = (
        ("ai_enabled", "AI Assistant", "ai", False),
        ("booking_enabled", "Booking", "commerce", False),
        ("multi_language", "Multi Language", "i18n", False),
    )

    def ensure_seeded(self) -> None:
        for code, name, category, default in self.MVP_FLAGS:
            if FeatureFlag.query.filter_by(code=code).first():
                continue
            db.session.add(
                FeatureFlag(
                    name=name,
                    code=code,
                    category=category,
                    default_value=default,
                    scope="tenant",
                    is_system=True,
                )
            )
        db.session.commit()

    def get_by_code(self, code: str) -> FeatureFlag:
        self.ensure_seeded()
        flag = FeatureFlag.query.filter_by(code=code).first()
        if not flag:
            raise NotFoundError(f"Feature flag '{code}' not found.")
        return flag

    def list_for_tenant(self, tenant_id: int) -> list[dict]:
        self.ensure_seeded()
        flags = FeatureFlag.query.order_by(FeatureFlag.code).all()
        result = []
        for flag in flags:
            override = FeatureFlagOverride.query.filter_by(
                feature_flag_id=flag.id, tenant_id=tenant_id
            ).first()
            result.append(
                {
                    **flag.to_dict(),
                    "value": override.value if override else flag.default_value,
                    "has_override": override is not None,
                }
            )
        return result

    def set_tenant_override(
        self,
        *,
        tenant_id: int,
        code: str,
        value: bool,
        reason: str | None = None,
        set_by: int | None = None,
    ) -> dict:
        flag = self.get_by_code(code)
        override = FeatureFlagOverride.query.filter_by(
            feature_flag_id=flag.id, tenant_id=tenant_id
        ).first()
        if not override:
            override = FeatureFlagOverride(
                feature_flag_id=flag.id,
                tenant_id=tenant_id,
                value=value,
            )
            db.session.add(override)
        override.value = value
        override.reason = reason
        override.set_by = set_by
        db.session.commit()
        return {**flag.to_dict(), "value": value, "has_override": True}
