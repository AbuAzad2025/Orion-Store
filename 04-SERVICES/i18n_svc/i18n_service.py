"""Locale resolution and seeding (wave 7 #60)."""

from __future__ import annotations

from flask import g, request
from i18n.locale import Locale

from core.exceptions import NotFoundError
from orion.extensions import db
from tenant.tenant import Tenant


class I18nService:
    FALLBACK_CHAIN = ("ar", "en")

    def ensure_locales_seeded(self) -> None:
        defaults = [
            ("ar", "العربية", "rtl"),
            ("en", "English", "ltr"),
            ("he", "עברית", "rtl"),
            ("fr", "Français", "ltr"),
        ]
        for code, name, direction in defaults:
            if Locale.query.filter_by(code=code).first():
                continue
            db.session.add(
                Locale(
                    code=code,
                    name=name,
                    direction=direction,
                    is_active=code in ("ar", "en"),
                )
            )
        db.session.commit()

    def list_active_locales(self) -> list[Locale]:
        self.ensure_locales_seeded()
        return Locale.query.filter_by(is_active=True).order_by(Locale.code).all()

    def get_locale(self, code: str) -> Locale:
        locale = Locale.query.filter_by(code=code, is_active=True).first()
        if not locale:
            raise NotFoundError(f"Locale '{code}' not found.")
        return locale

    def resolve_locale(
        self,
        tenant: Tenant | None,
        *,
        requested: str | None = None,
        multi_language_enabled: bool = True,
    ) -> str:
        self.ensure_locales_seeded()
        default = (tenant.default_language if tenant else None) or "ar"
        candidate = (requested or "").strip().lower()[:5] or None
        if not candidate:
            candidate = self._from_accept_language() or default
        if not multi_language_enabled and candidate != default:
            return default
        if Locale.query.filter_by(code=candidate, is_active=True).first():
            return candidate
        for code in self.FALLBACK_CHAIN:
            if Locale.query.filter_by(code=code, is_active=True).first():
                return code
        return default

    def _from_accept_language(self) -> str | None:
        header = request.headers.get("Accept-Language", "")
        if not header:
            return None
        primary = header.split(",")[0].strip().split(";")[0].strip()
        if "-" in primary:
            primary = primary.split("-")[0]
        return primary.lower()[:5] if primary else None

    def bind_request_locale(self) -> None:
        tenant = getattr(g, "tenant", None)
        requested = request.args.get("locale") or request.headers.get("X-Locale")
        multi = True
        if tenant:
            from feature_flag_svc.feature_flag_evaluator import FeatureFlagEvaluator

            multi = FeatureFlagEvaluator().is_enabled(tenant.id, "multi_language")
        g.locale = self.resolve_locale(
            tenant, requested=requested, multi_language_enabled=multi
        )
