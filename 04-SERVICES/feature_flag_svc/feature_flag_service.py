from __future__ import annotations

import hashlib

from core.exceptions import NotFoundError
from feature_flag.feature_flag import FeatureFlag, TenantFeatureFlagOverride
from feature_flag.feature_flag_override import FeatureFlagOverride
from orion.extensions import db


class FeatureFlagService:
    MVP_FLAGS = (
        ("ai_enabled", "AI Assistant", "ai", False),
        ("booking_enabled", "Booking", "commerce", False),
        ("multi_language", "Multi Language", "i18n", False),
        ("subscriptions_enabled", "Subscriptions", "commerce", False, 50),
        ("bopis_enabled", "BOPIS Pickup", "commerce", False, 30),
        ("store_credit_enabled", "Store Credit", "commerce", False, 50),
        ("draft_orders_enabled", "Draft Orders", "admin", True, 100),
        ("affiliates_enabled", "Affiliates", "marketing", False, 30),
        ("gift_registries_enabled", "Gift Registries", "marketing", False, 20),
        ("dropship_enabled", "Dropshipping", "commerce", False, 20),
        ("live_chat_enabled", "Live Chat", "support", False, 30),
    )

    def ensure_seeded(self) -> None:
        for flag_data in self.MVP_FLAGS:
            code = flag_data[0]
            if FeatureFlag.query.filter_by(code=code).first():
                continue
            rollout = flag_data[4] if len(flag_data) > 4 else 100
            db.session.add(
                FeatureFlag(
                    name=flag_data[1],
                    code=code,
                    category=flag_data[2],
                    default_value=flag_data[3],
                    scope="tenant",
                    is_system=True,
                    rollout_percent=rollout,
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
            override = TenantFeatureFlagOverride.query.filter_by(
                flag_id=flag.id, tenant_id=tenant_id
            ).first()
            if override:
                value = override.enabled
                override_info = {
                    "override_reason": override.reason,
                    "override_set_by": override.set_by,
                    "override_set_by_name": None,
                }
                if override.set_by:
                    from user.user import User

                    user = User.query.get(override.set_by)
                    if user:
                        override_info["override_set_by_name"] = user.name or user.email
            else:
                value = self._evaluate_rollout(flag, tenant_id)
                override_info = {}
            result.append(
                {
                    **flag.to_dict(),
                    "value": value,
                    "has_override": override is not None,
                    "rollout_percent": flag.rollout_percent,
                    **override_info,
                }
            )
        return result

    def is_enabled(self, *, tenant_id: int, code: str) -> bool:
        flag = self.get_by_code(code)
        override = TenantFeatureFlagOverride.query.filter_by(
            flag_id=flag.id, tenant_id=tenant_id
        ).first()
        if override:
            return override.enabled
        return self._evaluate_rollout(flag, tenant_id)

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
        override = TenantFeatureFlagOverride.query.filter_by(
            flag_id=flag.id, tenant_id=tenant_id
        ).first()
        if not override:
            override = TenantFeatureFlagOverride(
                flag_id=flag.id,
                tenant_id=tenant_id,
                enabled=value,
            )
            db.session.add(override)
        override.enabled = value
        override.reason = reason
        override.set_by = set_by
        db.session.commit()
        return {**flag.to_dict(), "value": value, "has_override": True}

    def remove_tenant_override(self, *, tenant_id: int, code: str) -> None:
        flag = self.get_by_code(code)
        override = TenantFeatureFlagOverride.query.filter_by(
            flag_id=flag.id, tenant_id=tenant_id
        ).first()
        if override:
            db.session.delete(override)
            db.session.commit()

    def _evaluate_rollout(self, flag: FeatureFlag, tenant_id: int) -> bool:
        if flag.rollout_percent >= 100:
            return flag.default_value
        if flag.rollout_percent <= 0:
            return False
        hash_input = f"{flag.id}:{tenant_id}".encode()
        digest = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
        return (digest % 100) < flag.rollout_percent
