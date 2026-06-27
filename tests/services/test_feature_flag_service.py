"""Feature flag service tests (wave 7)."""

from __future__ import annotations

from feature_flag_svc.feature_flag_evaluator import FeatureFlagEvaluator
from feature_flag_svc.feature_flag_service import FeatureFlagService

from tenant_svc.tenant_service import TenantService


def test_seed_and_override(app):
    flags = FeatureFlagService()
    flags.ensure_seeded()
    tenant = TenantService().create_tenant(
        name="FF Co", slug="ff-co", email="ff@test.com"
    )
    assert FeatureFlagEvaluator().is_enabled(tenant.id, "ai_enabled") is False
    flags.set_tenant_override(tenant_id=tenant.id, code="ai_enabled", value=True)
    assert FeatureFlagEvaluator().is_enabled(tenant.id, "ai_enabled") is True
    listed = flags.list_for_tenant(tenant.id)
    assert any(f["code"] == "multi_language" for f in listed)
