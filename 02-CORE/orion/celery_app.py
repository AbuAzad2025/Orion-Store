"""Celery application factory (§3.8, wave 15)."""

from __future__ import annotations

from celery import Celery

celery_app = Celery("orion")


def init_celery(app) -> Celery:
    broker = app.config.get("CELERY_BROKER_URL") or app.config.get("REDIS_URL")
    celery_app.conf.update(
        broker_url=broker,
        result_backend=app.config.get("CELERY_RESULT_BACKEND", broker),
        task_always_eager=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
        task_ignore_result=True,
    )

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    import notification_svc.tasks  # noqa: F401

    app.extensions["celery"] = celery_app
    return celery_app
