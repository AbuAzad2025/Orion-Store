"""CMS pages service (wave 15)."""

from __future__ import annotations

from i18n.cms_page import CmsPage
from i18n.page_translation import PageTranslation

from core.exceptions import ConflictError, NotFoundError, ValidationError
from orion.extensions import db


class PageService:
    def list_published(self, tenant_id: int) -> list[CmsPage]:
        return (
            CmsPage.query.filter_by(tenant_id=tenant_id, is_published=True)
            .order_by(CmsPage.slug)
            .all()
        )

    def list_all(self, tenant_id: int) -> list[CmsPage]:
        """Admin listing — includes drafts and unpublished (soft-deleted) pages."""
        return CmsPage.query.filter_by(tenant_id=tenant_id).order_by(CmsPage.slug).all()

    def get_by_slug(self, tenant_id: int, slug: str) -> CmsPage:
        page = CmsPage.query.filter_by(
            tenant_id=tenant_id, slug=slug, is_published=True
        ).first()
        if not page:
            raise NotFoundError("Page not found.")
        return page

    def get_by_id(self, tenant_id: int, page_id: int) -> CmsPage:
        page = CmsPage.query.filter_by(tenant_id=tenant_id, id=page_id).first()
        if not page:
            raise NotFoundError("Page not found.")
        return page

    def merge_translation(self, page: CmsPage, locale: str) -> dict:
        data = page.to_dict()
        trans = PageTranslation.query.filter_by(
            tenant_id=page.tenant_id, page_id=page.id, locale=locale
        ).first()
        if not trans:
            return {**data, "locale": locale, "body": None}
        data.update(
            {
                "locale": locale,
                "title": trans.title,
                "body": trans.body,
                "slug": trans.slug or page.slug,
            }
        )
        return data

    @staticmethod
    def _normalize_slug(value) -> str:
        slug = str(value or "").strip()
        if not slug:
            raise ValidationError("Slug is required.")
        return slug

    @staticmethod
    def _normalize_title(value) -> str:
        title = str(value or "").strip()
        if not title:
            raise ValidationError("Title is required.")
        return title

    def _ensure_unique_slug(
        self, tenant_id: int, slug: str, *, exclude_id: int | None = None
    ) -> None:
        query = CmsPage.query.filter_by(tenant_id=tenant_id, slug=slug)
        if exclude_id is not None:
            query = query.filter(CmsPage.id != exclude_id)
        if query.first():
            raise ConflictError("A page with this slug already exists.")

    def create_page(
        self, *, tenant_id: int, slug: str, title: str, is_published: bool = False
    ) -> CmsPage:
        slug = self._normalize_slug(slug)
        title = self._normalize_title(title)
        self._ensure_unique_slug(tenant_id, slug)
        page = CmsPage(
            tenant_id=tenant_id, slug=slug, title=title, is_published=is_published
        )
        db.session.add(page)
        db.session.commit()
        return page

    def update_page(
        self,
        page: CmsPage,
        *,
        slug: str | None = None,
        title: str | None = None,
        is_published: bool | None = None,
    ) -> CmsPage:
        if slug is not None:
            slug = self._normalize_slug(slug)
            self._ensure_unique_slug(page.tenant_id, slug, exclude_id=page.id)
            page.slug = slug
        if title is not None:
            page.title = self._normalize_title(title)
        if is_published is not None:
            page.is_published = bool(is_published)
        db.session.commit()
        return page

    def delete_page(self, page: CmsPage) -> None:
        """Soft delete — unpublish so the page disappears from the storefront.

        The CmsPage model has no deleted_at column; is_published is the
        visibility flag used by all public queries, so clearing it hides the
        page while keeping the record (and its translations) available to
        admins.
        """
        page.is_published = False
        db.session.commit()

    def upsert_translation(
        self,
        page: CmsPage,
        *,
        locale: str,
        title: str,
        body: str | None = None,
        slug: str | None = None,
    ) -> PageTranslation:
        locale = str(locale or "").strip().lower()
        if not locale:
            raise ValidationError("Locale is required.")
        title = self._normalize_title(title)
        row = PageTranslation.query.filter_by(
            tenant_id=page.tenant_id, page_id=page.id, locale=locale
        ).first()
        if not row:
            row = PageTranslation(
                tenant_id=page.tenant_id, page_id=page.id, locale=locale, title=title
            )
            db.session.add(row)
        else:
            row.title = title
        row.body = body
        row.slug = str(slug or "").strip() or None
        db.session.commit()
        return row
