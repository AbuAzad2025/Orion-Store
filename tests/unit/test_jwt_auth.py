"""JWT token unit tests (wave 1 gap closure)."""

from __future__ import annotations

from core.jwt_auth import issue_tokens_for_user


def test_issue_tokens_for_superuser(app):
    from auth.auth_service import AuthService

    with app.app_context():
        user = AuthService().register_super_admin(
            email="jwt@azadexa.com", password="password123"
        )
        tokens = issue_tokens_for_user(user)
    assert tokens["access_token"]
    assert tokens["refresh_token"]
