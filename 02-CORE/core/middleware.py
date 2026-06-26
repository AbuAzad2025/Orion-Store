"""HTTP middleware pipeline (§3.5)."""

from __future__ import annotations

import uuid

from flask import Flask, g, request
from sqlalchemy.orm import joinedload

from core.exceptions import AuthenticationError, NotFoundError
from orion.extensions import db
from tenant.tenant import Tenant
from user.user import User


def register_middleware(app: Flask) -> None:
    @app.before_request
    def resolve_tenant() -> None:
        g.tenant_id = None
        g.tenant = None
        g.user = None
        g.role = None
        g.is_platform_admin = False

        tenant = _resolve_tenant_from_request()
        if tenant:
            g.tenant_id = tenant.id
            g.tenant = tenant

        _resolve_user_from_header()

    @app.before_request
    def bind_tenant_rls() -> None:
        if g.tenant_id and db.engine.dialect.name == "postgresql":
            db.session.execute(
                db.text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(g.tenant_id)},
            )


def _resolve_tenant_from_request() -> Tenant | None:
    header_id = request.headers.get("X-Tenant-ID")
    if header_id:
        tenant = None
        try:
            tenant = _tenant_query().filter_by(public_id=uuid.UUID(header_id)).first()
        except ValueError:
            tenant = None
        if not tenant:
            tenant = _tenant_query().filter_by(slug=header_id).first()
        if tenant:
            return tenant

    host = (request.host or "").split(":")[0].lower()
    if host and host not in ("localhost", "127.0.0.1"):
        parts = host.split(".")
        if len(parts) >= 3:
            subdomain = parts[0]
            tenant = _tenant_query().filter_by(domain=subdomain).first()
            if tenant:
                return tenant
        tenant = _tenant_query().filter_by(custom_domain=host).first()
        if tenant:
            return tenant
    return None


def _tenant_query():
    return Tenant.query.options(joinedload(Tenant.config))


def _resolve_user_from_header() -> None:
    user_public_id = request.headers.get("X-User-ID")
    if not user_public_id:
        return
    try:
        uid = uuid.UUID(user_public_id)
    except ValueError:
        raise AuthenticationError("Invalid user context.") from None
    user = User.query.filter_by(public_id=uid, is_active=True).first()
    if not user:
        raise AuthenticationError("Invalid user context.")
    if user.is_superuser:
        if user.tenant_id is not None:
            raise AuthenticationError("Superuser must not have tenant_id.")
        g.user = user
        g.is_platform_admin = True
        g.role = "platform_admin"
        return
    if g.tenant_id and user.tenant_id != g.tenant_id:
        raise AuthenticationError("User does not belong to this tenant.")
    g.user = user
    g.role = "tenant_admin" if user.is_admin else "customer"


def require_platform_admin() -> None:
    if not g.is_platform_admin:
        raise AuthenticationError("Platform admin required.")


def require_tenant_context() -> Tenant:
    if not g.tenant:
        raise NotFoundError("Tenant context required.")
    return g.tenant
