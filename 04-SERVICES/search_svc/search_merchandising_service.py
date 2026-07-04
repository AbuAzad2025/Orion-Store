from __future__ import annotations

from core.exceptions import NotFoundError
from orion.extensions import db
from search.search import SearchBoostRule, SearchRedirect, SearchSynonym


class SearchMerchandisingService:
    def add_synonym(
        self, *, tenant_id: int, term: str, synonyms: list
    ) -> SearchSynonym:
        s = SearchSynonym(tenant_id=tenant_id, term=term, synonyms=synonyms)
        db.session.add(s)
        db.session.commit()
        return s

    def list_synonyms(self, tenant_id: int) -> list[SearchSynonym]:
        return SearchSynonym.query.filter_by(tenant_id=tenant_id).all()

    def add_redirect(
        self, *, tenant_id: int, query_term: str, redirect_url: str
    ) -> SearchRedirect:
        r = SearchRedirect(
            tenant_id=tenant_id, query_term=query_term, redirect_url=redirect_url
        )
        db.session.add(r)
        db.session.commit()
        return r

    def add_boost(
        self,
        *,
        tenant_id: int,
        product_id: int | None = None,
        category_id: int | None = None,
        boost_factor: int = 1,
        query_keyword: str | None = None,
    ) -> SearchBoostRule:
        b = SearchBoostRule(
            tenant_id=tenant_id,
            product_id=product_id,
            category_id=category_id,
            boost_factor=boost_factor,
            query_keyword=query_keyword,
        )
        db.session.add(b)
        db.session.commit()
        return b
