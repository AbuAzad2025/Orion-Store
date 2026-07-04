from app_platform.app_platform import OAuthApplication, SandboxStore
from app_platform_svc.app_platform_service import AppPlatformService
from flask import Blueprint, g, jsonify, request

from core.exceptions import OrionError
from core.middleware import require_tenant_admin

app_platform_bp = Blueprint("app_platform", __name__)
_svc = AppPlatformService()


@app_platform_bp.route("/apps", methods=["GET"])
def list_apps():
    try:
        require_tenant_admin()
        apps = OAuthApplication.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"apps": [a.to_dict() for a in apps]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@app_platform_bp.route("/sandboxes", methods=["GET"])
def list_sandboxes():
    try:
        require_tenant_admin()
        sandboxes = SandboxStore.query.filter_by(tenant_id=g.tenant_id).all()
        return jsonify({"sandboxes": [s.to_dict() for s in sandboxes]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@app_platform_bp.route("/apps", methods=["POST"])
def register_app():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        app = _svc.register_app(
            tenant_id=g.tenant_id,
            name=data["name"],
            redirect_uris=data.get("redirect_uris", []),
            scopes=data.get("scopes"),
        )
        return jsonify({"app": app.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@app_platform_bp.route("/apps/<int:app_id>/install", methods=["POST"])
def install_app(app_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        inst = _svc.install_app(
            tenant_id=g.tenant_id,
            app_id=app_id,
            installed_by=data.get("installed_by", 0),
        )
        return jsonify({"installation": inst.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@app_platform_bp.route(
    "/installations/<int:installation_id>/webhooks", methods=["POST"]
)
def subscribe_webhook(installation_id: int):
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        sub = _svc.subscribe_webhook(
            tenant_id=g.tenant_id,
            installation_id=installation_id,
            topic=data["topic"],
            callback_url=data["callback_url"],
        )
        return jsonify({"webhook": sub.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@app_platform_bp.route("/sandboxes", methods=["POST"])
def create_sandbox():
    try:
        require_tenant_admin()
        data = request.get_json(silent=True) or {}
        sb = _svc.create_sandbox(
            tenant_id=g.tenant_id,
            slug=data["slug"],
            name=data["name"],
            expires_at=data["expires_at"],
        )
        return jsonify({"sandbox": sb.to_dict()}), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400
