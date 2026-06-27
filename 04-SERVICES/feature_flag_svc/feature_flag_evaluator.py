"""Feature flag evaluation (wave 7 #61)."""

from __future__ import annotations

from feature_flag.feature_flag_override import FeatureFlagOverride
from feature_flag_svc.feature_flag_service import FeatureFlagService


class FeatureFlagEvaluator:
    def __init__(self) -> None:
        self._flags = FeatureFlagService()

    def is_enabled(self, tenant_id: int, code: str) -> bool:
        flag = self._flags.get_by_code(code)
        override = FeatureFlagOverride.query.filter_by(
            feature_flag_id=flag.id, tenant_id=tenant_id
        ).first()
        if override:
            return override.value
        return flag.default_value
