"""Auth service unit tests (wave 1)."""

from __future__ import annotations

import pytest

from auth.auth_service import AuthService
from core.exceptions import AuthenticationError, ValidationError


def test_short_password_rejected(app):
    auth = AuthService()
    with pytest.raises(ValidationError):
        auth.hash_password("short")


def test_duplicate_super_admin_rejected(app):
    auth = AuthService()
    auth.register_super_admin(email="dup@azadexa.com", password="password123")
    with pytest.raises(ValidationError):
        auth.register_super_admin(email="dup@azadexa.com", password="password123")


def test_authenticate_updates_last_login(app):
    auth = AuthService()
    auth.register_super_admin(email="login@azadexa.com", password="password123")
    user = auth.authenticate(
        email="login@azadexa.com", password="password123", tenant_id=None
    )
    assert user.last_login_at is not None


def test_authenticate_wrong_password(app):
    auth = AuthService()
    auth.register_super_admin(email="bad@azadexa.com", password="password123")
    with pytest.raises(AuthenticationError):
        auth.authenticate(
            email="bad@azadexa.com", password="wrong-password", tenant_id=None
        )
