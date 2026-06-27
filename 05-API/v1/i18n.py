"""i18n public + tenant APIs (wave 7 #60, wave 15 pages/glossary)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from i18n_svc.glossary_service import GlossaryService
from i18n_svc.i18n_service import I18nService
from i18n_svc.page_service import PageService

from core.context import get_locale
from core.exceptions import OrionError
from core.middleware import require_tenant_admin, require_tenant_context

i18n_bp = Blueprint("i18n", __name__)
_i18n = I18nService()
_pages = PageService()
_glossary = GlossaryService()


@i18n_bp.get("/languages")
def list_languages():
    try:
        locales = _i18n.list_active_locales()
        return jsonify({"languages": [loc.to_dict() for loc in locales]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@i18n_bp.get("/pages")
def list_pages():
    try:
        tenant = require_tenant_context()
        rows = _pages.list_published(tenant.id)
        locale = get_locale()
        return (
            jsonify(
                {"pages": [_pages.merge_translation(page, locale) for page in rows]}
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@i18n_bp.get("/pages/<slug>")
def get_page(slug: str):
    try:
        tenant = require_tenant_context()
        page = _pages.get_by_slug(tenant.id, slug)
        return (
            jsonify({"page": _pages.merge_translation(page, get_locale())}),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@i18n_bp.get("/glossary")
def list_glossary():
    try:
        tenant = require_tenant_context()
        source = request.args.get("source", "ar")
        target = request.args.get("target", "en")
        rows = _glossary.list_terms(
            tenant_id=tenant.id, source_locale=source, target_locale=target
        )
        return jsonify({"terms": [row.to_dict() for row in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@i18n_bp.post("/glossary")
def upsert_glossary_term():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        row = _glossary.upsert_term(
            tenant_id=g.tenant_id,
            source_locale=data["source_locale"],
            target_locale=data["target_locale"],
            source_term=data["source_term"],
            target_term=data["target_term"],
        )
        return jsonify({"term": row.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing glossary fields."}), 400
