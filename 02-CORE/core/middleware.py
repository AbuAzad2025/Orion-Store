"""HTTP middleware pipeline (§3.5)."""

from __future__ import annotations

import uuid

from flask import Flask, current_app, g, jsonify, redirect, request, session
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from sqlalchemy.orm import joinedload

from core.beta_gate import (
    beta_mode_enabled,
    enforce_beta_tenant_access,
    is_beta_gated_path,
)
from core.exceptions import AuthenticationError, AuthorizationError, NotFoundError
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
        g.impersonator_user = None
        g.impersonated_user = None

        tenant = _resolve_tenant_from_request()
        if tenant:
            g.tenant_id = tenant.id
            g.tenant = tenant

        # Users table is itself RLS-protected: bind context BEFORE querying it,
        # otherwise non-superuser runtime roles cannot authenticate at all.
        bind_rls_context()

        _resolve_authenticated_user()

        if g.user and g.user.tenant_id:
            g.tenant_id = g.user.tenant_id
            g.tenant = Tenant.query.get(g.user.tenant_id)

        if g.user:
            try:
                claims = get_jwt()
            except Exception:
                claims = {}
            impersonation = claims.get("impersonation") if claims else None
            if impersonation:
                g.impersonation_claims = impersonation
                g.impersonator_user = db.session.get(
                    User, impersonation.get("impersonator_user_id")
                )
                g.impersonated_user = g.user

        # Rebind after the user/role is known (platform-admin flag may change).
        bind_rls_context()

        # A signed JWT alone is not proof that impersonation is still allowed:
        # the session may have been ended/revoked/expired. Validate against
        # the database on every request so a stolen token cannot outlive it.
        if getattr(g, "impersonation_claims", None) and request.path not in (
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/admin/login",
            # Session lifecycle endpoints must stay callable even when the
            # current impersonation token is stale/expired.
            "/api/v1/start",
            "/api/v1/end",
            "/api/v1/status",
        ):
            claim = g.impersonation_claims
            try:
                from impersonation.impersonation_service import ImpersonationService

                tenant_id = claim.get("tenant_id") or getattr(g, "tenant_id", None)
                if not tenant_id and g.user:
                    tenant_id = getattr(g.user, "tenant_id", None)
                if not tenant_id:
                    raise AuthorizationError("Invalid impersonation context.")
                ImpersonationService().validate_session(
                    impersonator_user_id=int(claim["impersonator_user_id"]),
                    target_user_id=int(claim["target_user_id"]),
                    tenant_id=int(tenant_id),
                )
            except Exception:
                return (
                    jsonify({"error": "Impersonation session is no longer valid."}),
                    401,
                )

        _resolve_request_locale()

    @app.teardown_request
    def reset_rls_context(exception=None) -> None:
        if db.engine.dialect.name == "postgresql":
            db.session.execute(db.text("SELECT set_config('app.tenant_id', '', false)"))
            db.session.execute(
                db.text("SELECT set_config('app.is_platform_admin', 'false', false)")
            )

    @app.after_request
    def remember_debug_tenant(response):
        """In dev preview, remember the chosen tenant for subsequent bare URLs."""
        if current_app.debug and request.args.get("tenant_slug"):
            response.set_cookie(
                "orion_preview_tenant",
                request.args["tenant_slug"],
                max_age=7 * 24 * 3600,
                httponly=False,
                samesite="Lax",
            )
        return response

    @app.before_request
    def guard_beta_program() -> None:
        if not beta_mode_enabled() or not is_beta_gated_path(request.path):
            return None
        if g.is_platform_admin:
            return None
        try:
            enforce_beta_tenant_access(g.tenant.slug if g.tenant else None)
        except AuthorizationError as exc:
            from flask import jsonify

            return jsonify({"error": exc.message}), exc.status_code
        return None

    @app.before_request
    def guard_admin_html():
        path = request.path
        if not path.startswith("/admin"):
            return None
        if path.startswith("/admin/static") or path == "/admin/login":
            return None
        if path.startswith("/admin/platform"):
            if not g.user or not g.is_platform_admin:
                return redirect("/admin/login")
            return None
        if path.startswith("/admin/store"):
            if not g.tenant_id:
                return ("Tenant context required (X-Tenant-ID).", 404)
            if not g.user:
                return redirect("/admin/login")
            if not g.is_platform_admin and (
                not g.user.is_admin or g.user.tenant_id != g.tenant_id
            ):
                return ("Forbidden", 403)
        return None


def bind_rls_context() -> None:
    """Bind tenant and platform-admin flags to the current DB transaction.

    Called from before_request and from code that establishes tenant context
    after middleware (e.g. webhook handlers).
    """
    from flask import has_app_context

    if not has_app_context() or db.engine.dialect.name != "postgresql":
        return
    db.session.execute(
        db.text("SELECT set_config('app.tenant_id', :tid, false)"),
        {"tid": str(g.tenant_id) if g.tenant_id else ""},
    )
    db.session.execute(
        db.text("SELECT set_config('app.is_platform_admin', :flag, false)"),
        {"flag": "true" if g.get("is_platform_admin") else "false"},
    )


def bind_task_rls_context(
    tenant_id: int | None = None, *, is_platform_admin: bool = False
) -> None:
    """Bind RLS context for background jobs (no Flask request context)."""
    if db.engine.dialect.name != "postgresql":
        return
    db.session.execute(
        db.text("SELECT set_config('app.tenant_id', :tid, false)"),
        {"tid": str(tenant_id) if tenant_id else ""},
    )
    db.session.execute(
        db.text("SELECT set_config('app.is_platform_admin', :flag, false)"),
        {"flag": "true" if is_platform_admin else "false"},
    )


def _resolve_request_locale() -> None:
    from i18n_svc.i18n_service import I18nService

    I18nService().bind_request_locale()


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

    # The read-only tenants/me endpoint is also allowed in debug preview so
    # local tooling can inspect which tenant the fallback resolved.
    debug_api_preview = request.path == "/api/v1/tenants/me"
    if current_app.debug and (
        debug_api_preview or not request.path.startswith(("/api/", "/admin/"))
    ):
        preview_slug = request.args.get("tenant_slug") or request.cookies.get(
            "orion_preview_tenant"
        )
        if preview_slug:
            tenant = _tenant_query().filter_by(slug=preview_slug).first()
            if tenant:
                return tenant
        # Last resort for local development only: first active tenant.
        tenant = (
            _tenant_query()
            .filter_by(is_active=True, deleted_at=None)
            .order_by(Tenant.id)
            .first()
        )
        if tenant:
            return tenant
    return None


def _tenant_query():
    return Tenant.query.options(joinedload(Tenant.config))


def _resolve_authenticated_user() -> None:
    """JWT (API) or session (HTML admin)."""
    if request.path in ("/api/v1/auth/refresh", "/admin/login"):
        return
    try:
        verify_jwt_in_request(optional=True, locations=["cookies", "headers"])
    except Exception:
        identity = None  # missing/invalid JWT → anonymous, but not swallowed below
    else:
        identity = get_jwt_identity()
    if identity:
        # AuthenticationError from a mismatched tenant must propagate as 401,
        # never silently downgrade the request to anonymous.
        _bind_user_to_context(str(identity))
        return

    # API must not fall back to the HTML admin session (CSRF-exempt APIs).
    if request.path.startswith("/api/") or "user_id" not in session:
        return

    if "user_id" in session:
        user = User.query.filter_by(id=session["user_id"], is_active=True).first()
        if user:
            g.user = user
            g.is_platform_admin = user.is_superuser
            g.role = (
                "platform_admin"
                if user.is_superuser
                else ("tenant_admin" if user.is_admin else "customer")
            )
            return


def _bind_user_to_context(user_public_id: str) -> None:
    try:
        uid = uuid.UUID(user_public_id)
    except (ValueError, TypeError):
        # Legacy clients/test helpers use a slug as identity. Treat as anonymous;
        # a real (valid UUID) token from another tenant is still rejected below.
        return
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


def require_tenant_admin() -> None:
    if not g.tenant_id or not g.user:
        raise AuthenticationError("Tenant context required.")
    if g.is_platform_admin:
        return
    if not g.user.is_admin or g.user.tenant_id != g.tenant_id:
        raise AuthorizationError("Tenant admin required.")


def require_tenant_context() -> Tenant:
    if not g.tenant:
        raise NotFoundError("Tenant context required.")
    return g.tenant
