"""Application factory."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from core.event_handlers import register_domain_event_handlers
from core.exceptions import OrionError
from core.i18n_messages import translate_message
from core.middleware import register_middleware
from core.monitoring import register_monitoring
from core.rate_limit import init_rate_limiter
from core.redis_cache import RedisCache, ping_redis
from core.security_headers import register_security_headers
from orion.config import config_by_name
from orion.extensions import csrf, db, jwt, migrate
from v1.routes import API_BLUEPRINTS, register_blueprints, register_ui_blueprints


def _is_placeholder(value: str) -> bool:
    return not value or bool(
        re.match(r"^(change[_-]?me|dev[_-]?only|changeme|xxx|placeholder)", value, re.I)
    )


def _validate_production_secrets(app: Flask) -> None:
    """Refuse to boot production with placeholder or malformed secrets."""
    invalid: list[str] = []
    secret = str(app.config.get("SECRET_KEY") or "")
    if _is_placeholder(secret) or len(secret) < 32:
        invalid.append("SECRET_KEY")
    jwt_secret = str(app.config.get("JWT_SECRET_KEY") or "")
    if _is_placeholder(jwt_secret) or len(jwt_secret) < 32:
        invalid.append("JWT_SECRET_KEY")
    enc = str(app.config.get("ENCRYPTION_KEY") or "")
    try:
        Fernet(enc.encode())
    except Exception:
        invalid.append("ENCRYPTION_KEY")
    if invalid:
        raise RuntimeError(
            "Production startup blocked — missing or placeholder secrets: "
            + ", ".join(invalid)
        )


def _validate_production_rls(app: Flask) -> None:
    """Refuse to boot if tenant RLS is not actually enforced.

    The runtime role owns the tenant tables, so RLS is inert until FORCE is
    applied. This guard prevents a release from starting if a migration was
    skipped during deployment.
    """
    if os.environ.get("ORION_SKIP_RLS_CHECK") == "1":
        return
    from orion.extensions import db

    if db.engine.dialect.name != "postgresql":
        raise RuntimeError("Production requires PostgreSQL with forced RLS.")
    forced = db.session.execute(
        db.text(
            "SELECT relforcerowsecurity FROM pg_class "
            "WHERE relname = 'users' AND relkind = 'r'"
        )
    ).scalar()
    if not forced:
        raise RuntimeError(
            "Production startup blocked — tenant RLS is not forced. "
            "Run flask db upgrade before activating the release."
        )


def _asset_version() -> str:
    """Hash the committed theme CSS so asset URLs change whenever it changes."""
    css = Path(__file__).resolve().parents[2] / "01-FOUNDATION/assets/orion-theme.css"
    try:
        return hashlib.sha256(css.read_bytes()).hexdigest()[:8]
    except OSError:  # pragma: no cover - deployed images always ship the file
        return "static"


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.jinja_env.globals["asset_version"] = _asset_version()
    env = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["default"]))

    # Behind the production TLS reverse proxy the app sees HTTP on :5000.
    # Trust the proxy headers so request.is_secure, host-based tenant resolution
    # and Secure cookie redirects behave as they do on the public HTTPS origin.
    if env == "production":
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
        )

    # Config class attributes are evaluated at import time, before load_dotenv()
    # runs. Re-apply critical environment values so .env and late-set vars win.
    for key in (
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "ENCRYPTION_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "PRODUCT_IMAGES_DIR",
        "MAX_CONTENT_LENGTH",
        "MAX_IMAGES_PER_TENANT",
        "MAX_IMAGE_BYTES_PER_TENANT",
    ):
        value = os.environ.get(key)
        if value is not None:
            if key == "PRODUCT_IMAGES_DIR":
                value = str(Path(value).expanduser().resolve())
            elif key in (
                "MAX_CONTENT_LENGTH",
                "MAX_IMAGES_PER_TENANT",
                "MAX_IMAGE_BYTES_PER_TENANT",
            ):
                value = int(value)
            app.config[key] = value

    # JWT_SECRET_KEY defaults to the import-time SECRET_KEY (placeholder).
    # Derive it from the real, re-applied secret when not explicitly provided.
    if "JWT_SECRET_KEY" not in os.environ:
        app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]

    if app.config.get("ENV") == "production":
        if app.debug:
            raise RuntimeError(
                "Production mode requires DEBUG=False; "
                "check FLASK_ENV and DEBUG env vars."
            )
        _validate_production_secrets(app)

    db.init_app(app)
    if app.config.get("ENV") == "production":
        with app.app_context():
            _validate_production_rls(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    from core.jwt_auth import install_token_blocklist

    install_token_blocklist(jwt)
    csrf.init_app(app)

    import discount.voucher  # noqa: F401
    import feature_flag.feature_flag  # noqa: F401
    import feature_flag.feature_flag_override  # noqa: F401
    import i18n.category_translation  # noqa: F401
    import i18n.cms_page  # noqa: F401
    import i18n.locale  # noqa: F401
    import i18n.page_translation  # noqa: F401
    import i18n.product_translation  # noqa: F401
    import i18n.translation_glossary  # noqa: F401
    import shipping.shipping_method  # noqa: F401
    import shipping.shipping_rate  # noqa: F401
    import shipping.shipping_zone  # noqa: F401

    import b2b.customer_group  # noqa: F401
    import b2b.price_list  # noqa: F401
    import b2b.quote  # noqa: F401
    import base.base_model  # noqa: F401
    import bnpl.bnpl_provider  # noqa: F401
    import bnpl.bnpl_transaction  # noqa: F401
    import bundle.bundle  # noqa: F401
    import catalog.brand  # noqa: F401
    import catalog.category  # noqa: F401
    import catalog.product  # noqa: F401
    import oms.fulfillment  # noqa: F401
    import oms.warehouse  # noqa: F401
    import order.cart  # noqa: F401
    import order.order  # noqa: F401
    import payment.payment  # noqa: F401
    import payment.refund  # noqa: F401
    import platform_models.audit_log  # noqa: F401
    import platform_models.commission_ledger  # noqa: F401
    import platform_models.financial_event  # noqa: F401
    import platform_models.invoice  # noqa: F401
    import platform_models.platform_settings  # noqa: F401
    import platform_models.revoked_token  # noqa: F401
    import platform_models.tenant_gateway  # noqa: F401
    import returns.merchandise_return  # noqa: F401
    import returns.return_reason  # noqa: F401
    import tenant.tenant  # noqa: F401
    import tenant.tenant_config  # noqa: F401
    import user.role  # noqa: F401
    import user.user  # noqa: F401

    register_blueprints(app)
    for bp in API_BLUEPRINTS:
        csrf.exempt(bp)
    register_ui_blueprints(app)
    register_middleware(app)
    register_security_headers(app)
    register_monitoring(app)
    init_rate_limiter(app)
    app.extensions["redis_cache"] = RedisCache(app.config.get("REDIS_URL"))
    from core.store_token import issue as issue_store_token
    from core.store_token import signed_url
    from engine.whatsapp import whatsapp_url

    app.jinja_env.globals["whatsapp_url"] = whatsapp_url
    app.jinja_env.globals["store_token_for"] = lambda tenant: (
        issue_store_token(tenant) if tenant else ""
    )
    app.jinja_env.globals["signed_image_url"] = signed_url

    from orion.celery_app import init_celery

    init_celery(app)
    register_domain_event_handlers()

    @app.get("/health")
    def health() -> tuple[dict, int]:
        redis_url = app.config.get("REDIS_URL")
        return (
            jsonify(
                {
                    "status": "ok",
                    "service": "azadexa-orion",
                    "redis": ping_redis(redis_url),
                }
            ),
            200,
        )

    @app.get("/ready")
    def ready() -> tuple[dict, int]:
        try:
            db.session.execute(db.text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        redis_url = app.config.get("REDIS_URL")
        redis_ok = ping_redis(redis_url) if redis_url else False
        require_redis = bool(redis_url) and app.config.get("ENV") == "production"
        is_ready = db_ok and (redis_ok or not require_redis)
        return (
            jsonify(
                {
                    "status": "ready" if is_ready else "not_ready",
                    "database": db_ok,
                    "redis": redis_ok,
                }
            ),
            200 if is_ready else 503,
        )

    @app.after_request
    def translate_api_errors(response):
        """Localise the ``error`` field when the caller explicitly asks a locale.

        Only requests carrying ``X-Locale`` (sent by our UI clients) or an
        explicit ``?locale=`` are translated. Plain API clients and tests keep
        receiving the canonical service message, preserving the API contract.
        """
        explicit_locale = request.headers.get("X-Locale") or request.args.get("locale")
        if not explicit_locale or not response.is_json:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict):
            return response
        message = payload.get("error")
        if not isinstance(message, str):
            return response
        translated = translate_message(message, explicit_locale)
        if translated != message:
            payload["error"] = translated
            response.set_data(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            )
        return response

    @app.errorhandler(OrionError)
    def handle_orion_error(exc: OrionError):
        return jsonify({"error": exc.message}), exc.status_code

    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def handle_expected_http_error(exc):
        return jsonify({"error": exc.description or exc.name}), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        from werkzeug.exceptions import HTTPException

        if isinstance(exc, HTTPException):
            return jsonify({"error": exc.description or exc.name}), exc.code or 500
        app.logger.exception("Unhandled error %s %s", request.method, request.path)
        return jsonify({"error": "An unexpected error occurred."}), 500

    return app
