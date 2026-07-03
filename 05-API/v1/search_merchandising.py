from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin
from search.search import SearchBoostRule, SearchRedirect
from search_svc.search_merchandising_service import SearchMerchandisingService

search_bp = Blueprint("search", __name__)
_svc = SearchMerchandisingService()


@search_bp.route("/synonyms", methods=["GET"])
def list_synonyms():
    try:
        require_tenant_admin()
        return jsonify({"synonyms": [s.to_dict() for s in _svc.list_synonyms(g.tenant_id)]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@search_bp.route("/synonyms", methods=["POST"])
def add_synonym():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        s = _svc.add_synonym(tenant_id=g.tenant_id, term=data["term"], synonyms=data["synonyms"])
        return jsonify({"synonym": s.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@search_bp.route("/redirects", methods=["GET"])
def list_redirects():
    try:
        require_tenant_admin()
        redirects = SearchRedirect.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"redirects": [r.to_dict() for r in redirects]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@search_bp.route("/redirects", methods=["POST"])
def add_redirect():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        r = _svc.add_redirect(tenant_id=g.tenant_id, query_term=data["query_term"], redirect_url=data["redirect_url"])
        return jsonify({"redirect": r.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@search_bp.route("/boosts", methods=["GET"])
def list_boosts():
    try:
        require_tenant_admin()
        boosts = SearchBoostRule.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"boosts": [b.to_dict() for b in boosts]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@search_bp.route("/boosts", methods=["POST"])
def add_boost():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        b = _svc.add_boost(
            tenant_id=g.tenant_id, product_id=data.get("product_id"),
            category_id=data.get("category_id"),
            boost_factor=int(data.get("boost_factor", 1)),
            query_keyword=data.get("query_keyword"),
        )
        return jsonify({"boost": b.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
