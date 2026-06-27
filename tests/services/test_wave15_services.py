"""Email, Celery, and notification coverage (wave 15)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from notification_svc.email_sender import render_order_confirmation, send_smtp_email
from notification_svc.notification_service import NotificationService
from notification_svc.tasks import check_trial_expiry_task, send_email_task
from order.order import Order


def test_render_order_confirmation():
    subject, body = render_order_confirmation(
        {"order_number": "ORD-1", "total": "99.00"}
    )
    assert "ORD-1" in subject
    assert "99.00" in body


def test_send_smtp_email(app):
    app.config.update(
        {
            "SMTP_HOST": "smtp.test",
            "SMTP_PORT": 587,
            "SMTP_USER": "u",
            "SMTP_PASSWORD": "p",
            "SMTP_FROM": "noreply@test.com",
            "SMTP_USE_TLS": True,
        }
    )
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    with app.app_context():
        with patch(
            "notification_svc.email_sender.smtplib.SMTP", return_value=mock_client
        ):
            send_smtp_email(recipient="a@b.com", subject="Hi", body="Body")
    mock_client.starttls.assert_called_once()
    mock_client.send_message.assert_called_once()


def test_notification_sends_when_smtp_configured(app):
    app.config.update(
        {
            "SMTP_HOST": "smtp.test",
            "SMTP_PORT": 587,
            "CELERY_TASK_ALWAYS_EAGER": True,
        }
    )
    order = Order(
        tenant_id=1,
        customer_email="buyer@test.com",
        order_number="ORD-2",
        total="10.00",
    )
    with app.app_context():
        with patch("notification_svc.email_sender.smtplib.SMTP") as smtp:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            smtp.return_value = mock_client
            row = NotificationService().send_order_confirmation(order)
    assert row["status"] == "sent"


def test_send_email_task(app):
    app.config.update({"SMTP_HOST": "smtp.test", "SMTP_PORT": 587})
    payload = {
        "template": "order_confirmation",
        "recipient": "x@y.com",
        "context": {"order_number": "O-1", "total": "5"},
    }
    with app.app_context():
        with patch("notification_svc.email_sender.smtplib.SMTP") as smtp:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            smtp.return_value = mock_client
            result = send_email_task(payload)
    assert result["status"] == "sent"


def test_check_trial_expiry_task(app):
    from base.types import TenantStatus
    from tenant_svc.tenant_service import TenantService

    tenant = TenantService().create_tenant(
        name="Trial", slug="trial-exp", email="trial@test.com"
    )
    tenant.status = TenantStatus.TRIAL.value
    from orion.extensions import db

    db.session.commit()
    with app.app_context():
        count = check_trial_expiry_task()
    assert count >= 1
    db.session.refresh(tenant)
    assert tenant.status == TenantStatus.SUSPENDED.value


def test_palpay_live_missing_credentials():
    from integrations.payments.palpay import charge_palpay
    from platform_models.tenant_gateway import TenantPaymentGateway

    gateway = TenantPaymentGateway(
        tenant_id=1,
        provider="palpay",
        display_name="PalPay",
        is_enabled=True,
        is_sandbox=False,
        status="active",
    )
    order = Order(
        tenant_id=1,
        order_number="ORD-X",
        customer_email="t@test.com",
        shipping_address={},
        total="1",
    )
    order.id = 1
    result = charge_palpay(order=order, gateway=gateway, amount="1.00")
    assert result["success"] is False


def test_glossary_apply():
    from i18n.translation_glossary import TranslationGlossary
    from i18n_svc.glossary_service import GlossaryService

    term = TranslationGlossary(
        id=1,
        tenant_id=1,
        source_locale="ar",
        target_locale="en",
        source_term="متجر",
        target_term="store",
    )
    assert GlossaryService().apply_glossary("متجرنا", [term]) == "storeنا"
