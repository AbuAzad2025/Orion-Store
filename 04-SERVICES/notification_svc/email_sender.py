"""SMTP email delivery."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage


def smtp_configured() -> bool:
    try:
        from flask import current_app

        return bool(current_app.config.get("SMTP_HOST"))
    except RuntimeError:
        return False


def send_smtp_email(*, recipient: str, subject: str, body: str) -> None:
    from flask import current_app

    host = current_app.config["SMTP_HOST"]
    port = int(current_app.config.get("SMTP_PORT", 587))
    user = current_app.config.get("SMTP_USER", "")
    password = current_app.config.get("SMTP_PASSWORD", "")
    sender = current_app.config.get("SMTP_FROM", user or "noreply@azadexa.com")
    use_tls = current_app.config.get("SMTP_USE_TLS", True)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=15) as client:
        if use_tls:
            client.starttls()
        if user and password:
            client.login(user, password)
        client.send_message(msg)


def render_order_confirmation(context: dict) -> tuple[str, str]:
    subject = f"تأكيد الطلب {context.get('order_number', '')}"
    body = (
        f"شكراً لطلبك من Azadexa.\n"
        f"رقم الطلب: {context.get('order_number')}\n"
        f"الإجمالي: {context.get('total')}\n"
    )
    return subject, body
