"""Unified in-store sign-in: one form, routed by account type."""

from __future__ import annotations

from flask import g, redirect, request, session
from flask_jwt_extended import set_access_cookies, set_refresh_cookies

from core.jwt_auth import issue_tokens_for_user
from core.middleware import bind_rls_context


def handle_store_login(tenant) -> object:
    from auth.auth_service import AuthService

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    try:
        bind_rls_context()
        user = AuthService().authenticate(
            email=email, password=password, tenant_id=tenant.id
        )
    except Exception:
        user = None
    if user is None or getattr(user, "tenant_id", None) != tenant.id:
        return redirect(f"/s/{tenant.slug}/login?error=1")
    session["user_id"] = user.id
    session["tenant_id"] = user.tenant_id
    session["is_platform_admin"] = False
    session.permanent = True
    resp = redirect("/admin/store/dashboard" if user.is_admin else "/account")
    tokens = issue_tokens_for_user(user)
    set_access_cookies(resp, tokens["access_token"])
    set_refresh_cookies(resp, tokens["refresh_token"])
    return resp
