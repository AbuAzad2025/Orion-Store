"""Feature flag evaluation — single path through FeatureFlagService."""

from __future__ import annotations

from feature_flag_svc.feature_flag_service import FeatureFlagService


class FeatureFlagEvaluator:
    """Compatibility facade; all evaluation lives in FeatureFlagService."""

    def __init__(self) -> None:
        self._flags = FeatureFlagService()

    def is_enabled(self, tenant_id: int, code: str) -> bool:
        return self._flags.is_enabled(tenant_id=tenant_id, code=code)
