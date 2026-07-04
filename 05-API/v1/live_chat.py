from flask import Blueprint, g, jsonify, request
from live_chat.live_chat import LiveChatSession
from live_chat_svc.live_chat_service import LiveChatService

from core.exceptions import OrionError
from core.middleware import require_tenant_admin

live_chat_bp = Blueprint("live_chat", __name__)
_svc = LiveChatService()


@live_chat_bp.route("/sessions", methods=["GET"])
def list_sessions():
    try:
        require_tenant_admin()
        sessions = (
            LiveChatSession.query.filter_by(tenant_id=g.tenant_id)
            .order_by(LiveChatSession.created_at.desc())
            .all()
        )
        return jsonify({"sessions": [s.to_dict() for s in sessions]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@live_chat_bp.route("/sessions", methods=["POST"])
def create_session():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        session = _svc.create_session(
            tenant_id=g.tenant_id, customer_email=data.get("customer_email")
        )
        return jsonify({"session": session.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@live_chat_bp.route("/sessions/<int:session_id>/messages", methods=["GET"])
def get_messages(session_id: int):
    try:
        require_tenant_admin()
        messages = _svc.get_messages(tenant_id=g.tenant_id, session_id=session_id)
        return jsonify({"messages": [m.to_dict() for m in messages]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@live_chat_bp.route("/sessions/<int:session_id>/messages", methods=["POST"])
def send_message(session_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        msg = _svc.send_message(
            tenant_id=g.tenant_id,
            session_id=session_id,
            sender_type=data["sender_type"],
            message=data["message"],
        )
        return jsonify({"message": msg.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
