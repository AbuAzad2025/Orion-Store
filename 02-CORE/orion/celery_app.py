"""Celery application — configured at import time so beat/worker see it too."""

from __future__ import annotations

import os

from celery import Celery

celery_app = Celery("orion")

BEAT_SCHEDULE = {
    "check-trial-expiry-hourly": {
        "task": "orion.check_trial_expiry",
        "schedule": 3600.0,
    },
    "reconciliation-nightly": {
        "task": "orion.reconciliation.run_nightly",
        "schedule": 86400.0,
    },
    "expire-whatsapp-orders-daily": {
        "task": "orion.expire_whatsapp_orders",
        "schedule": 86400.0,
    },
}

_default_broker = (
    os.environ.get("CELERY_BROKER_URL")
    or os.environ.get("REDIS_URL")
    or "redis://127.0.0.1:6379/0"
)
celery_app.conf.update(
    broker_url=_default_broker,
    result_backend=os.environ.get("CELERY_RESULT_BACKEND", _default_broker),
    task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower()
    in ("1", "true", "yes"),
    task_ignore_result=True,
    beat_schedule=BEAT_SCHEDULE,
)


_task_app = None


def _build_task_app():
    """Minimal app for beat/worker processes (no blueprint registration)."""
    from flask import Flask
    from orion.extensions import db

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app


class ContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        global _task_app
        if _task_app is None:
            _task_app = _build_task_app()
        with _task_app.app_context():
            from core.middleware import bind_task_rls_context

            bind_task_rls_context()
            return self.run(*args, **kwargs)


celery_app.Task = ContextTask

import notification_svc.tasks  # noqa: E402,F401
import order_svc.tasks  # noqa: E402,F401


def init_celery(app) -> Celery:
    global _task_app
    _task_app = app
    broker = app.config.get("CELERY_BROKER_URL") or app.config.get("REDIS_URL")
    if broker:
        celery_app.conf.update(
            broker_url=broker,
            result_backend=app.config.get("CELERY_RESULT_BACKEND", broker),
            task_always_eager=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
            beat_schedule=BEAT_SCHEDULE,
        )
    app.extensions["celery"] = celery_app
    return celery_app
