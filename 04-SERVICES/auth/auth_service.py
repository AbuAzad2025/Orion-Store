"""Authentication service."""

from __future__ import annotations

import bcrypt
from flask import g

from core.context import get_user
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from core.utils import utc_now
from orion.extensions import db
from user.role import Role, UserRole
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
        if User.query.filter(
            User.is_superuser.is_(True), User.tenant_id.is_(None)
        ).first():
            raise ValidationError(
                "Super admin already exists. Platform admin bootstrap is one-time only."
            )
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
        from core.rls_elevation import platform_read

        query = User.query.filter_by(email=email, is_active=True, deleted_at=None)
        if tenant_id is None:
            query = query.filter_by(is_superuser=True, tenant_id=None)
        else:
            query = query.filter_by(tenant_id=tenant_id, is_superuser=False)
        with platform_read():
            user = query.first()
            if not user or not self.verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid credentials.")
            # The user row is RLS-protected: flush the login-time write while
            # elevated, and keep the loaded attributes available after the
            # transaction so callers never re-query under a blocked context.
            user.last_login_at = utc_now()
            db.session.flush()
            session = db.session()
            previous = session.expire_on_commit
            session.expire_on_commit = False
            try:
                db.session.commit()
            finally:
                session.expire_on_commit = previous
            db.session.expunge(user)
        g.user = user
        return user

    def assign_role(self, tenant_id: int, user_id: int, role_code: str) -> UserRole:
        """Assign a tenant-scoped role to a user after ownership checks.

        Both sides must belong to ``tenant_id``: a user from another tenant
        (or a role owned by another tenant) is rejected. Re-assigning an
        existing role is idempotent.
        """
        user = db.session.get(User, user_id)
        if not user or user.deleted_at is not None:
            raise NotFoundError("User not found.")
        if user.tenant_id != tenant_id:
            raise AuthorizationError("User does not belong to this tenant.")

        role = Role.query.filter_by(tenant_id=tenant_id, code=role_code).first()
        if not role:
            raise NotFoundError("Role not found for this tenant.")

        existing = UserRole.query.filter_by(user_id=user.id, role_id=role.id).first()
        if existing:
            return existing

        actor = get_user()
        assignment = UserRole(
            user_id=user.id,
            role_id=role.id,
            assigned_by=actor.id if actor is not None else None,
        )
        db.session.add(assignment)
        db.session.commit()
        return assignment
