"""CMS pages service (wave 15)."""

from __future__ import annotations

from i18n.cms_page import CmsPage
from i18n.page_translation import PageTranslation

from core.exceptions import NotFoundError
from orion.extensions import db


class PageService:
    def list_published(self, tenant_id: int) -> list[CmsPage]:
        return (
            CmsPage.query.filter_by(tenant_id=tenant_id, is_published=True)
            .order_by(CmsPage.slug)
            .all()
        )

    def get_by_slug(self, tenant_id: int, slug: str) -> CmsPage:
        page = CmsPage.query.filter_by(
            tenant_id=tenant_id, slug=slug, is_published=True
        ).first()
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

    def create_page(
        self, *, tenant_id: int, slug: str, title: str, is_published: bool = False
    ) -> CmsPage:
        page = CmsPage(
            tenant_id=tenant_id, slug=slug, title=title, is_published=is_published
        )
        db.session.add(page)
        db.session.commit()
        return page
