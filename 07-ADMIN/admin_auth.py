"""Shared admin login page."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, g, redirect, render_template, request, session, url_for
from flask_jwt_extended import (
    set_access_cookies,
    set_refresh_cookies,
    unset_access_cookies,
    unset_refresh_cookies,
)

from auth.auth_service import AuthService
from core.jwt_auth import issue_tokens_for_user
from core.rate_limit import limiter
from platform_svc.platform_settings_service import PlatformSettingsService
from tenant.tenant import Tenant

_ADMIN_ROOT = Path(__file__).resolve().parent

admin_auth_bp = Blueprint(
    "admin_auth",
    __name__,
    template_folder=str(_ADMIN_ROOT / "templates"),
)

_auth = AuthService()


@admin_auth_bp.context_processor
def inject_platform_settings():
    try:
        settings = PlatformSettingsService().get_singleton()
    except Exception:
        settings = None
    return {"platform_settings": settings}


@admin_auth_bp.get("/login")
def admin_login():
    return render_template("admin_login.html", page_title="تسجيل الدخول", error=None)


@admin_auth_bp.post("/login")
@limiter.limit("5 per minute")
def admin_login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    tenant_slug = request.form.get("tenant_slug", "").strip()

    tenant_id = None
    if tenant_slug:
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if tenant:
            tenant_id = tenant.id

    try:
        user = _auth.authenticate(email=email, password=password, tenant_id=tenant_id)
    except Exception:
        return (
            render_template(
                "admin_login.html",
                page_title="تسجيل الدخول",
                error="Invalid credentials",
            ),
            401,
        )

    session["user_id"] = user.id
    session["tenant_id"] = user.tenant_id
    session["is_platform_admin"] = bool(user.is_superuser)
    session.permanent = True

    tokens = issue_tokens_for_user(user)
    resp = redirect(
        "/admin/platform/dashboard" if user.is_superuser else "/admin/store/dashboard"
    )
    set_access_cookies(resp, tokens["access_token"])
    set_refresh_cookies(resp, tokens["refresh_token"])
    return resp


@admin_auth_bp.get("/logout")
def admin_logout():
    session.clear()
    resp = redirect("/admin/login")
    resp.set_cookie("session", "", expires=0)
    unset_access_cookies(resp)
    unset_refresh_cookies(resp)
    return resp


@admin_auth_bp.get("/profile")
def admin_profile():
    if not g.user:
        return redirect("/admin/login")
    return render_template(
        "admin_profile.html",
        page_title="الملف الشخصي",
        user=g.user,
        tenant=g.tenant,
        is_platform_admin=g.is_platform_admin,
    )
