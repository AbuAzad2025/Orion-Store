"""Authentication service."""

from __future__ import annotations

import bcrypt
from flask import g

from core.exceptions import AuthenticationError, ValidationError
from core.utils import utc_now
from orion.extensions import db
from user.user import User


class AuthService:
    def hash_password(self, password: str) -> str:
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def register_super_admin(
        self, *, email: str, password: str, first_name: str = "Platform"
    ) -> User:
        if User.query.filter_by(email=email, tenant_id=None).first():
            raise ValidationError("Super admin already exists.")
        user = User(
            email=email,
            password_hash=self.hash_password(password),
            first_name=first_name,
            is_superuser=True,
            is_customer=False,
            is_admin=True,
            tenant_id=None,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def register_tenant_user(
        self,
        *,
        tenant_id: int,
        email: str,
        password: str,
        is_admin: bool = True,
    ) -> User:
        if User.query.filter_by(email=email, tenant_id=tenant_id).first():
            raise ValidationError("Email already registered for this tenant.")
        user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=self.hash_password(password),
            is_admin=is_admin,
            is_customer=not is_admin,
            is_superuser=False,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def authenticate(self, *, email: str, password: str, tenant_id: int | None) -> User:
        query = User.query.filter_by(email=email, is_active=True, deleted_at=None)
        if tenant_id is None:
            query = query.filter_by(is_superuser=True, tenant_id=None)
        else:
            query = query.filter_by(tenant_id=tenant_id, is_superuser=False)
        user = query.first()
        if not user or not self.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials.")
        user.last_login_at = utc_now()
        db.session.commit()
        g.user = user
        return user
