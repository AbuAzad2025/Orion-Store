"""Round-8 regression: readiness backup gate is platform-only and fail-closed."""

from __future__ import annotations

import json
import time

from core.monitoring import backup_freshness, readiness_dependencies


def _heartbeat(tmp_path, *, kind, age, stamp="20261128T020000Z"):
    path = tmp_path / "heartbeat.json"
    path.write_text(
        json.dumps({"kind": kind, "stamp": stamp, "updated_at": time.time() - age}),
        encoding="utf-8",
    )
    return str(path)


def test_backup_freshness_accepts_only_fresh_platform_heartbeats(tmp_path):
    ok, info = backup_freshness(_heartbeat(tmp_path, kind="platform", age=5), 60)
    assert ok is True
    assert info["backup"] is True
    assert info["backup_kind"] == "platform"
    assert info["backup_stamp"] == "20261128T020000Z"
    ok, info = backup_freshness(_heartbeat(tmp_path, kind="store", age=5), 60)
    assert ok is False
    ok, _ = backup_freshness(_heartbeat(tmp_path, kind="platform", age=5000), 60)
    assert ok is False
    assert backup_freshness("", 60) == (False, {"backup": False})
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert backup_freshness(str(bad), 60) == (False, {"backup": False})


def test_readiness_dependencies_honour_the_backup_gate(app, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "READY_REQUIRE_BACKUP", True)
    monkeypatch.setitem(app.config, "BACKUP_HEARTBEAT_MAX_AGE_SECONDS", 60)
    monkeypatch.setitem(
        app.config, "BACKUP_HEARTBEAT_FILE", _heartbeat(tmp_path, kind="store", age=5)
    )
    extra, failed = readiness_dependencies()
    assert failed is True
    assert extra["backup"] is False
    monkeypatch.setitem(
        app.config,
        "BACKUP_HEARTBEAT_FILE",
        _heartbeat(tmp_path, kind="platform", age=5),
    )
    extra, failed = readiness_dependencies()
    assert failed is False
    assert extra["backup"] is True
