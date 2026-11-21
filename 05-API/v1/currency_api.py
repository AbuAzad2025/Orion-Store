from decimal import Decimal, InvalidOperation

from currency.currency_rate import CurrencyRate
from currency_svc.currency_service import CurrencyService
from flask import Blueprint, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_platform_admin

currency_bp = Blueprint("currency", __name__)
_svc = CurrencyService()


@currency_bp.route("/rates", methods=["GET"])
def list_rates():
    try:
        require_platform_admin()
        rates = (
            CurrencyRate.query.order_by(CurrencyRate.created_at.desc()).limit(100).all()
        )
        return jsonify({"rates": [r.to_dict() for r in rates]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@currency_bp.route("/rates", methods=["POST"])
def set_rate():
    try:
        require_platform_admin()
        data = request.get_json(silent=True) or {}
        rate = _svc.set_rate(
            from_currency=data["from_currency"],
            to_currency=data["to_currency"],
            rate=data["rate"],
            source=data.get("source", "manual"),
        )
        return jsonify({"rate": rate.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@currency_bp.route("/convert", methods=["GET"])
def convert():
    try:
        amount = Decimal(request.args.get("amount", "0"))
        from_cur = request.args.get("from", "ILS")
        to_cur = request.args.get("to", "ILS")
        result = _svc.convert(amount=amount, from_currency=from_cur, to_currency=to_cur)
        return (
            jsonify(
                {
                    "amount": str(amount),
                    "from": from_cur,
                    "to": to_cur,
                    "result": str(result),
                }
            ),
            200,
        )
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (TypeError, ValueError, InvalidOperation):
        return jsonify({"error": "Invalid request."}), 400
