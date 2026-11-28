"""Tenant business logic."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from flask import current_app
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from base.types import TenantStatus
from core.exceptions import NotFoundError, ValidationError
from orion.extensions import db
from tenant.tenant import Tenant
from tenant.tenant_config import TenantConfig

logger = logging.getLogger(__name__)

ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"trial", "active", "cancelled"}),
    "trial": frozenset({"active", "suspended", "cancelled"}),
    "active": frozenset({"suspended", "cancelled"}),
    "suspended": frozenset({"active", "cancelled"}),
    "cancelled": frozenset(),
}
_VALID_STATUSES = frozenset(s.value for s in TenantStatus)


class TenantService:
    def list_tenants(self) -> list[Tenant]:
        return (
            Tenant.query.options(joinedload(Tenant.config))
            .filter(Tenant.deleted_at.is_(None))
            .order_by(Tenant.created_at.desc())
            .all()
        )

    def get_by_public_id(self, public_id: str) -> Tenant:
        tenant = (
            Tenant.query.options(joinedload(Tenant.config))
            .filter_by(public_id=public_id, deleted_at=None)
            .first()
        )
        if not tenant:
            raise NotFoundError("Tenant not found.")
        return tenant

    def create_tenant(
        self,
        *,
        name: str,
        name_en: str | None = None,
        logo_url: str | None = None,
        slug: str,
        email: str,
        domain: str | None = None,
        status: str | None = None,
    ) -> Tenant:
        if status is not None:
            if status not in _VALID_STATUSES:
                raise ValidationError("Invalid tenant status.")
            if status == "cancelled":
                raise ValidationError("New tenants cannot be created as cancelled.")
        if Tenant.query.filter_by(slug=slug).first():
            raise ValidationError("Slug already exists.")
        tenant = Tenant(
            name=name,
            name_en=name_en,
            logo_url=logo_url,
            slug=slug,
            email=email,
            domain=domain or slug,
            status=status or TenantStatus.TRIAL.value,
        )
        tenant.config = TenantConfig(business_name=name)
        db.session.add(tenant)
        db.session.commit()

        self.ensure_asset_folder(slug)
        self.ensure_policy_pages(tenant.id)

        from core.audit_log import audit_log

        audit_log(
            action="tenant.created",
            resource_type="tenant",
            resource_id=str(tenant.id),
            tenant_id=tenant.id,
            details={"slug": tenant.slug, "name": tenant.name},
        )

        from integrations.external_registry import register_tenant_subdomain

        # DNS/routing registration is best-effort: a failed external call must
        # not roll back an already-persisted (and audited) tenant or surface as
        # a 5xx that would make the caller retry and create a duplicate.
        try:
            register_tenant_subdomain(slug=tenant.slug, tenant_id=tenant.id)
        except Exception as exc:
            logger.warning(
                "Subdomain registration failed for tenant %s (%s): %s",
                tenant.slug,
                tenant.id,
                exc,
            )
        return tenant

    @staticmethod
    def ensure_policy_pages(tenant_id: int) -> None:
        """Seed minimal published privacy/terms pages for a new store."""
        from i18n.cms_page import CmsPage
        from i18n.page_translation import PageTranslation

        seeds = (
            (
                "privacy",
                "سياسة الخصوصية",
                "Privacy Policy",
                "نحن نحترم خصوصيتك ولا نشارك بياناتك مع أطراف ثالثة.",
                "We respect your privacy and do not share your data with third parties.",
            ),
            (
                "terms",
                "الشروط والأحكام",
                "Terms & Conditions",
                "باستخدام المتجر فإنك توافق على الشروط والأحكام.",
                "By using this store you agree to the terms and conditions.",
            ),
        )
        for slug, ar_title, en_title, ar_body, en_body in seeds:
            page = CmsPage.query.filter_by(tenant_id=tenant_id, slug=slug).first()
            if page is None:
                page = CmsPage(
                    tenant_id=tenant_id, slug=slug, title=ar_title, is_published=True
                )
                db.session.add(page)
                db.session.flush()
            else:
                page.is_published = True
            for locale, title, body in (
                ("ar", ar_title, ar_body),
                ("en", en_title, en_body),
            ):
                row = PageTranslation.query.filter_by(
                    tenant_id=tenant_id, page_id=page.id, locale=locale
                ).first()
                if row is None:
                    db.session.add(
                        PageTranslation(
                            tenant_id=tenant_id,
                            page_id=page.id,
                            locale=locale,
                            title=title,
                            body=body,
                            slug=slug,
                        )
                    )
                else:
                    row.title, row.body, row.slug = title, body, slug
        db.session.commit()

    @staticmethod
    def ensure_asset_folder(slug: str) -> Path | None:
        """Create the per-store product image folder (isolated assets)."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", (slug or "").lower()):
            return None
        try:
            from orion.paths import store_folder

            return store_folder(slug.lower())
        except Exception as exc:  # pragma: no cover - filesystem edge cases
            logger.warning("asset folder for %s failed: %s", slug, exc)
            return None

    def list_users_for_tenant(self, tenant_id: int):
        from user.user import User

        return User.query.filter_by(tenant_id=tenant_id, deleted_at=None).all()

    @staticmethod
    def validate_status_transition(
        current: str, target: str, *, allow_restore: bool = False
    ) -> None:
        if target not in _VALID_STATUSES:
            raise ValidationError("Invalid tenant status.")
        if target == current:
            return
        if target in ALLOWED_STATUS_TRANSITIONS.get(current, frozenset()):
            return
        if allow_restore and current == "cancelled" and target == "active":
            return
        raise ValidationError(
            f"Invalid tenant status transition: {current} -> {target}."
        )

    @staticmethod
    def _get_by_id(tenant_id: int, *, include_deleted: bool = False) -> Tenant:
        query = Tenant.query.options(joinedload(Tenant.config))
        if not include_deleted:
            query = query.filter(Tenant.deleted_at.is_(None))
        tenant = query.filter_by(id=tenant_id).first()
        if not tenant:
            raise NotFoundError("Tenant not found.")
        return tenant

    @staticmethod
    def _assert_identity_available(tenant: Tenant) -> None:
        values = [v for v in (tenant.slug, tenant.domain, tenant.custom_domain) if v]
        clash = (
            Tenant.query.filter(Tenant.id != tenant.id)
            .filter(
                or_(
                    Tenant.slug.in_(values),
                    Tenant.domain.in_(values),
                    Tenant.custom_domain.in_(values),
                )
            )
            .first()
        )
        if clash:
            raise ValidationError(
                "Cannot restore tenant: slug or domain is already in use."
            )

    def restore(self, tenant_id: int) -> Tenant:
        from core.audit_log import audit_log

        tenant = self._get_by_id(tenant_id, include_deleted=True)
        previous = tenant.status
        was_deleted = tenant.deleted_at is not None
        if not (was_deleted or previous in ("cancelled", "suspended")):
            raise ValidationError(
                "Only cancelled, suspended, or deleted tenants can be restored."
            )
        self.validate_status_transition(previous, "active", allow_restore=True)
        self._assert_identity_available(tenant)
        tenant.deleted_at = None
        tenant.is_active = True
        tenant.status = "active"
        tenant.suspended_until = None
        tenant.suspended_reason = None
        tenant.version += 1
        db.session.commit()
        audit_log(
            action="tenant.restored",
            resource_type="tenant",
            resource_id=str(tenant.id),
            tenant_id=tenant.id,
            details={
                "from_status": previous,
                "to_status": "active",
                "slug": tenant.slug,
                "undeleted": was_deleted,
            },
        )
        return tenant

    def reactivate(self, tenant_id: int) -> Tenant:
        from core.audit_log import audit_log

        tenant = self._get_by_id(tenant_id)
        if tenant.status != "suspended":
            raise ValidationError("Only suspended tenants can be reactivated.")
        self.validate_status_transition(tenant.status, "active")
        self._assert_identity_available(tenant)
        tenant.status = "active"
        tenant.suspended_until = None
        tenant.suspended_reason = None
        tenant.is_active = True
        tenant.version += 1
        db.session.commit()
        audit_log(
            action="tenant.reactivated",
            resource_type="tenant",
            resource_id=str(tenant.id),
            tenant_id=tenant.id,
            details={
                "from_status": "suspended",
                "to_status": "active",
                "slug": tenant.slug,
            },
        )
        return tenant
