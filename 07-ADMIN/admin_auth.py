"""Shared admin login page."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, render_template

_ADMIN_ROOT = Path(__file__).resolve().parent

admin_auth_bp = Blueprint(
    "admin_auth",
    __name__,
    template_folder=str(_ADMIN_ROOT / "templates"),
)


@admin_auth_bp.get("/login")
def admin_login():
    return render_template("admin_login.html", page_title="تسجيل الدخول")
