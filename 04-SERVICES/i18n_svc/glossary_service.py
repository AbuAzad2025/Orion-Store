"""Translation glossary service (wave 15)."""

from __future__ import annotations

from i18n.translation_glossary import TranslationGlossary

from orion.extensions import db


class GlossaryService:
    def list_terms(
        self, *, tenant_id: int | None, source_locale: str, target_locale: str
    ) -> list[TranslationGlossary]:
        return (
            TranslationGlossary.query.filter_by(
                tenant_id=tenant_id,
                source_locale=source_locale,
                target_locale=target_locale,
            )
            .order_by(TranslationGlossary.source_term)
            .all()
        )

    def upsert_term(
        self,
        *,
        tenant_id: int | None,
        source_locale: str,
        target_locale: str,
        source_term: str,
        target_term: str,
    ) -> TranslationGlossary:
        row = TranslationGlossary.query.filter_by(
            tenant_id=tenant_id,
            source_locale=source_locale,
            target_locale=target_locale,
            source_term=source_term.strip(),
        ).first()
        if not row:
            row = TranslationGlossary(
                tenant_id=tenant_id,
                source_locale=source_locale,
                target_locale=target_locale,
                source_term=source_term.strip(),
                target_term=target_term.strip(),
            )
            db.session.add(row)
        else:
            row.target_term = target_term.strip()
        db.session.commit()
        return row

    def apply_glossary(self, text: str, terms: list[TranslationGlossary]) -> str:
        result = text
        for term in terms:
            result = result.replace(term.source_term, term.target_term)
        return result
