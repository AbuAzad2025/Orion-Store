"""B2B wholesale API (wave 9 #63)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from b2b.quote import QuoteItem
from b2b_svc.b2b_service import B2bService
from core.exceptions import OrionError
from core.middleware import require_tenant_admin

b2b_bp = Blueprint("b2b", __name__)
_b2b = B2bService()


@b2b_bp.get("/customer-groups")
def list_customer_groups():
    try:
        require_tenant_admin()
        groups = _b2b.list_customer_groups(g.tenant_id)
        return jsonify({"groups": [grp.to_dict() for grp in groups]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@b2b_bp.post("/customer-groups")
def create_customer_group():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        group = _b2b.create_customer_group(
            tenant_id=g.tenant_id,
            name=data["name"],
            code=data["code"],
            discount_percent=data.get("discount_percent", "0"),
            payment_terms_days=int(data.get("payment_terms_days", 0)),
            is_wholesale=bool(data.get("is_wholesale", False)),
            price_list_id=data.get("price_list_id"),
        )
        return jsonify({"group": group.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing name or code."}), 400


@b2b_bp.post("/price-lists")
def create_price_list():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        pl = _b2b.create_price_list(tenant_id=g.tenant_id, name=data["name"])
        return jsonify({"price_list": pl.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing name."}), 400


@b2b_bp.post("/price-lists/<int:list_id>/items")
def add_price_item(list_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        item = _b2b.add_price_item(
            tenant_id=g.tenant_id,
            price_list_id=list_id,
            product_id=data["product_id"],
            price=data["price"],
            min_quantity=int(data.get("min_quantity", 1)),
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing product_id or price."}), 400


@b2b_bp.post("/quotes")
def create_quote():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        quote = _b2b.create_quote(
            tenant_id=g.tenant_id,
            customer_group_id=data.get("customer_group_id"),
            notes=data.get("notes"),
        )
        return jsonify({"quote": quote.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@b2b_bp.post("/quotes/<int:quote_id>/items")
def add_quote_item(quote_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        item = _b2b.add_quote_item(
            tenant_id=g.tenant_id,
            quote_id=quote_id,
            product_id=data["product_id"],
            quantity=int(data["quantity"]),
            discount_percent=data.get("discount_percent", "0"),
        )
        return jsonify({"item": item.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing product_id or quantity."}), 400


@b2b_bp.post("/quotes/<int:quote_id>/convert")
def convert_quote(quote_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        order = _b2b.convert_quote_to_order(
            tenant_id=g.tenant_id,
            quote_id=quote_id,
            customer_email=data["customer_email"],
            shipping_address=data.get("shipping_address"),
        )
        return jsonify({"order": order.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except KeyError:
        return jsonify({"error": "Missing customer_email."}), 400


@b2b_bp.get("/quotes/<int:quote_id>")
def get_quote(quote_id: int):
    try:
        require_tenant_admin()
        from b2b.quote import Quote

        quote = Quote.query.filter_by(id=quote_id, tenant_id=g.tenant_id).first()
        if not quote:
            return jsonify({"error": "Quote not found."}), 404
        items = QuoteItem.query.filter_by(quote_id=quote.id).all()
        return (
            jsonify(
                {
                    "quote": quote.to_dict(),
                    "items": [i.to_dict() for i in items],
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
