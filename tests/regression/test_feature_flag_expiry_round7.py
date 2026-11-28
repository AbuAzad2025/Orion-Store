"""Round-7 regression: expired legacy flag overrides stop applying everywhere."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from feature_flag.feature_flag_override import FeatureFlagOverride
from feature_flag_svc.feature_flag_evaluator import FeatureFlagEvaluator
from feature_flag_svc.feature_flag_service import FeatureFlagService

from orion.extensions import db
from tenant_svc.tenant_service import TenantService


def test_expired_legacy_override_is_ignored_by_both_evaluators(app):
    tenant = TenantService().create_tenant(
        name="Flag Store", slug="flag-store", email="flag@test.com"
    )
    flags = FeatureFlagService()
    flags.ensure_seeded()
    flag = flags.get_by_code("ai_enabled")

    row = FeatureFlagOverride(
        feature_flag_id=flag.id,
        tenant_id=tenant.id,
        value=True,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.session.add(row)
    db.session.commit()
    assert flags.is_enabled(tenant_id=tenant.id, code="ai_enabled") is True
    assert FeatureFlagEvaluator().is_enabled(tenant.id, "ai_enabled") is True

    row.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.session.commit()
    assert flags.is_enabled(tenant_id=tenant.id, code="ai_enabled") is False
    assert FeatureFlagEvaluator().is_enabled(tenant.id, "ai_enabled") is False
