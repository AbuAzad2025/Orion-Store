"""Scheduled platform backup (Celery Beat) with fail-closed worker capability."""

from __future__ import annotations

import os

from orion.celery_app import celery_app

WORKER_CAPABILITY_ENV = "ORION_BACKUP_WORKER_CAPABLE"


def worker_capability_enabled() -> bool:
    """True only on workers explicitly commissioned to run the sudo wrapper."""
    return os.environ.get(WORKER_CAPABILITY_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


@celery_app.task(name="orion.platform_backup.scheduled")
def scheduled_platform_backup() -> dict:
    """Create a platform backup via the restricted wrapper; never leak stderr."""
    if not worker_capability_enabled():
        return {"status": "skipped", "reason": "worker_capability_disabled"}
    from backup_svc.backup_service import BackupError, BackupService

    try:
        info = BackupService().create_platform()
    except BackupError:
        # Wrapper stderr may contain secrets — only a stable reason escapes.
        return {"status": "error", "reason": "backup_failed"}
    return {"status": "ok", "kind": "platform", "stamp": str(info.get("stamp", ""))}
