"""Automatic fraud-rule evaluation in the order lifecycle."""

from __future__ import annotations

import pytest

from auth.auth_service import AuthService
from core.events import publish
from core.exceptions import NotFoundError
from fraud.fraud import FraudReview
from fraud_svc.fraud_service import FraudService
from order.order import Order
from orion.extensions import db
from support.http import auth_headers
from tenant_svc.tenant_service import TenantService


@pytest.fixture
def tenant(app):
    with app.app_context():
        return TenantService().create_tenant(
            name="Fraud Eval", slug="fraud-eval", email="fraud@test.com"
        )


def _make_order(
    tenant_id: int,
    *,
    total: str = "10",
    email: str = "buyer@test.com",
    number: str = "FR-1",
) -> Order:
    """Create an order inside an active app context."""
    order = Order(
        tenant_id=tenant_id,
        order_number=number,
        customer_email=email,
        is_guest=True,
        shipping_address={},
        subtotal=total,
        total=total,
    )
    db.session.add(order)
    db.session.commit()
    return order


def _high_value_rule(tenant_id: int) -> None:
    FraudService().create_rule(
        tenant_id=tenant_id,
        name="High value",
        rule_type="amount",
        operator="gt",
        threshold_value="100",
    )


def test_high_amount_rule_creates_review(app, tenant):
    with app.app_context():
        _high_value_rule(tenant.id)
        order = _make_order(tenant.id, total="500")

        result = FraudService().evaluate_order(
            tenant_id=tenant.id, order_id=order.id, context={}
        )

        assert result["decision"] == "review"
        assert result["created"] is True
        assert 0 <= result["risk_score"] <= 100
        assert result["risk_score"] == 40
        reviews = FraudReview.query.filter_by(
            tenant_id=tenant.id, order_id=order.id
        ).all()
        assert len(reviews) == 1
        assert reviews[0].risk_score == result["risk_score"]


def test_low_amount_does_not_create_review(app, tenant):
    with app.app_context():
        _high_value_rule(tenant.id)
        order = _make_order(tenant.id, total="50")

        result = FraudService().evaluate_order(tenant_id=tenant.id, order_id=order.id)

        assert result["decision"] == "approve"
        assert result["risk_score"] == 0
        assert result["created"] is False
        assert (
            FraudReview.query.filter_by(
                tenant_id=tenant.id, order_id=order.id
            ).count()
            == 0
        )


def test_repeated_evaluation_is_idempotent(app, tenant):
    with app.app_context():
        _high_value_rule(tenant.id)
        order = _make_order(tenant.id, total="500")

        first = FraudService().evaluate_order(tenant_id=tenant.id, order_id=order.id)
        second = FraudService().evaluate_order(tenant_id=tenant.id, order_id=order.id)

        assert first["created"] is True
        assert second["created"] is False
        assert second["review"]["id"] == first["review"]["id"]
        assert (
            FraudReview.query.filter_by(
                tenant_id=tenant.id, order_id=order.id
            ).count()
            == 1
        )


def test_other_tenant_does_not_see_review(app, tenant):
    with app.app_context():
        other = TenantService().create_tenant(
            name="Other", slug="other-tenant", email="other@test.com"
        )
        _high_value_rule(tenant.id)
        order = _make_order(tenant.id, total="500")
        FraudService().evaluate_order(tenant_id=tenant.id, order_id=order.id)

        assert FraudReview.query.filter_by(tenant_id=other.id).count() == 0
        assert (
            FraudReview.query.filter_by(
                tenant_id=other.id, order_id=order.id
            ).count()
            == 0
        )
        with pytest.raises(NotFoundError):
            FraudService().evaluate_order(
                tenant_id=other.id, order_id=order.id
            )


def test_order_created_event_records_review(app, tenant):
    with app.app_context():
        _high_value_rule(tenant.id)
        order = _make_order(tenant.id, total="500")

        publish("order.created", tenant_id=tenant.id, order_id=order.id)

        assert (
            FraudReview.query.filter_by(
                tenant_id=tenant.id, order_id=order.id
            ).count()
            == 1
        )


def test_api_evaluate_sets_reviewed_from_current_user(app, client, tenant):
    with app.app_context():
        _high_value_rule(tenant.id)
        order = _make_order(tenant.id, total="500")
        admin = AuthService().register_tenant_user(
            tenant_id=tenant.id,
            email="admin@fraud.com",
            password="password123",
            is_admin=True,
        )
        admin_id = admin.id
        order_id = order.id
        headers = auth_headers(admin, app=app, tenant_id=tenant.slug)

    res = client.post(
        "/api/v1/fraud/evaluate", headers=headers, json={"order_id": order_id}
    )

    assert res.status_code == 200
    body = res.get_json()
    assert body["decision"] == "review"
    assert body["created"] is True
    assert 0 <= body["risk_score"] <= 100
    with app.app_context():
        review = FraudReview.query.filter_by(
            tenant_id=tenant.id, order_id=order.id
        ).one()
        assert review.reviewed_by == admin_id


def test_api_evaluate_rejects_other_tenant_order(app, client, tenant):
    with app.app_context():
        other = TenantService().create_tenant(
            name="Other API", slug="other-api", email="otherapi@test.com"
        )
        order = _make_order(tenant.id, total="500")
        admin = AuthService().register_tenant_user(
            tenant_id=other.id,
            email="admin@otherapi.com",
            password="password123",
            is_admin=True,
        )
        order_id = order.id
        headers = auth_headers(admin, app=app, tenant_id=other.slug)

    res = client.post(
        "/api/v1/fraud/evaluate", headers=headers, json={"order_id": order_id}
    )

    assert res.status_code == 404
    with app.app_context():
        assert FraudReview.query.count() == 0
