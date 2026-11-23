"""Admin login page — branded, accessible, behavior-preserving."""

from __future__ import annotations


def test_admin_login_page_is_branded_and_accessible(client, app) -> None:
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert 'class="orion-auth-card"' in text
    assert 'class="orion-auth-brand"' in text
    assert 'id="login-form" action="/admin/login" method="post"' in text
    assert 'id="email" name="email" type="email" required' in text
    assert 'id="password" name="password" type="password" required' in text
    assert 'aria-label="البريد الإلكتروني"' in text
    assert 'aria-label="كلمة المرور"' in text
    assert 'action="/admin/sso/exchange" method="post"' in text
    assert 'class="orion-btn orion-btn-gold orion-auth-btn"' in text


def test_admin_login_error_is_announced(client, app) -> None:
    resp = client.post(
        "/admin/login",
        data={"email": "nobody@example.test", "password": "wrong", "tenant_slug": ""},
    )
    assert resp.status_code == 401
    text = resp.get_data(as_text=True)
    assert 'class="orion-auth-error" role="alert"' in text
