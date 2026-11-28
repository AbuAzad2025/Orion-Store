"""Round-10 regression: scheduled backup capability gate + freshness gate."""

from __future__ import annotations

import json
import time

from backup_svc import tasks as backup_tasks
from core.monitoring import backup_freshness
from orion.celery_app import BEAT_SCHEDULE

CANARY = "LEAKCANARY_PLACEHOLDER_7A3F"


def _heartbeat(tmp_path, *, kind, age, stamp="20261128T030000Z"):
    path = tmp_path / "heartbeat.json"
    path.write_text(
        json.dumps({"kind": kind, "stamp": stamp, "updated_at": time.time() - age}),
        encoding="utf-8",
    )
    return str(path)


def test_worker_capability_gate_skips_by_default(monkeypatch):
    monkeypatch.delenv("ORION_BACKUP_WORKER_CAPABLE", raising=False)
    called = []
    monkeypatch.setattr(
        "backup_svc.backup_service.BackupService.create_platform",
        lambda self: called.append(1),
    )
    result = backup_tasks.scheduled_platform_backup.apply(throw=True).get()
    assert result == {"status": "skipped", "reason": "worker_capability_disabled"}
    assert called == []


def test_scheduled_backup_runs_when_capable(monkeypatch):
    monkeypatch.setenv("ORION_BACKUP_WORKER_CAPABLE", "1")
    monkeypatch.setattr(
        "backup_svc.backup_service.BackupService.create_platform",
        lambda self: {
            "name": "orionstore_full_x.dump",
            "kind": "platform",
            "stamp": "20261128T030000Z",
            "size": 1,
            "dump": "orionstore_full_x.dump",
            "assets": None,
        },
    )
    result = backup_tasks.scheduled_platform_backup.apply(throw=True).get()
    assert result == {"status": "ok", "kind": "platform", "stamp": "20261128T030000Z"}


def test_scheduled_backup_hides_wrapper_errors(monkeypatch):
    from backup_svc.backup_service import BackupError

    monkeypatch.setenv("ORION_BACKUP_WORKER_CAPABLE", "true")

    def boom(self):
        raise BackupError(CANARY)

    monkeypatch.setattr("backup_svc.backup_service.BackupService.create_platform", boom)
    result = backup_tasks.scheduled_platform_backup.apply(throw=True).get()
    assert result["status"] == "error"
    assert CANARY not in json.dumps(result)


def test_beat_schedule_registers_platform_backup():
    entry = BEAT_SCHEDULE["platform-backup-daily"]
    assert entry["task"] == "orion.platform_backup.scheduled"
    assert entry["schedule"] == 86400.0


def test_freshness_gate_accepts_only_fresh_platform_heartbeats(tmp_path):
    ok, info = backup_freshness(_heartbeat(tmp_path, kind="platform", age=5), 60)
    assert ok is True and info["backup"] is True
    assert (
        backup_freshness(
            _heartbeat(tmp_path, kind="store:palestinian-heritage", age=5), 60
        )[0]
        is False
    )
