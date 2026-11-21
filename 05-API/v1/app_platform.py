from app_platform.app_platform import (
    AppInstallation,
    AppWebhookSubscription,
    OAuthApplication,
    SandboxStore,
)
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
        # The raw client_secret exists only in this response. It is never
        # persisted (only a salted SHA-256 digest is) and never returned by
        # list_apps / to_dict afterwards.
        raw_secret = getattr(app, "_raw_client_secret", None)
        app_data = app.to_dict()
        if raw_secret:
            app_data["client_secret"] = raw_secret
        body = {"app": app_data}
        if raw_secret:
            body["client_secret"] = raw_secret
        return jsonify(body), 201
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid request."}), 400


@app_platform_bp.route("/apps/<int:app_id>/installations", methods=["GET"])
def list_installations(app_id: int):
    try:
        require_tenant_admin()
        rows = AppInstallation.query.filter_by(
            tenant_id=g.tenant_id, app_id=app_id
        ).all()
        return jsonify({"installations": [r.to_dict() for r in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@app_platform_bp.route("/installations/<int:installation_id>/webhooks", methods=["GET"])
def list_webhook_subscriptions(installation_id: int):
    try:
        require_tenant_admin()
        rows = AppWebhookSubscription.query.filter_by(
            tenant_id=g.tenant_id, installation_id=installation_id
        ).all()
        return jsonify({"webhooks": [r.to_dict() for r in rows]}), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@app_platform_bp.route("/apps/<int:app_id>/install", methods=["POST"])
def install_app(app_id: int):
    try:
        require_tenant_admin()
        # Installership is an authenticated fact, never client input. Ignore
        # any "installed_by" supplied in the body (previously defaulted to 0).
        inst = _svc.install_app(
            tenant_id=g.tenant_id,
            app_id=app_id,
            installed_by=g.user.id,
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


def _oauth_request_data() -> dict:
    """Accept JSON, form-encoded bodies, and HTTP Basic client credentials."""
    if request.is_json:
        data = dict(request.get_json(silent=True) or {})
    else:
        data = request.form.to_dict()
    auth = request.authorization
    if auth:
        data.setdefault("client_id", auth.username)
        data.setdefault("client_secret", auth.password)
    return data


def _issue_oauth_token(*, require_grant_type: bool):
    try:
        data = _oauth_request_data()
        grant_type = data.get("grant_type") or "client_credentials"
        if require_grant_type and grant_type != "client_credentials":
            return jsonify({"error": "Unsupported grant_type."}), 400
        result = _svc.issue_oauth_token(
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            scope=data.get("scope"),
            grant_type=grant_type,
        )
        return jsonify(result), 200
    except OrionError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid client credentials."}), 400


@app_platform_bp.route("/oauth/authorize", methods=["POST"])
def oauth_authorize():
    """Issue a signed access token for a registered app (implicit-style)."""
    return _issue_oauth_token(require_grant_type=False)


@app_platform_bp.route("/oauth/token", methods=["POST"])
def oauth_token():
    """OAuth2 client_credentials token endpoint for external applications."""
    return _issue_oauth_token(require_grant_type=True)
