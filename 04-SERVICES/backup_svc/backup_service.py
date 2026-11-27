"""Admin-UI backup creation/download service (no restore, no secrets)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path("/srv/apps/orionstore/shared/backups")
WRAPPER = Path("/srv/scripts/orion_backup_web.sh")
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class BackupError(RuntimeError):
    pass


class BackupService:
    def _run(self, action: str, slug: str | None = None) -> None:
        cmd = ["sudo", "-n", str(WRAPPER), action]
        if slug is not None:
            cmd.append(slug)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=900, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise BackupError(str(exc)) from exc
        if result.returncode != 0:
            raise BackupError(
                (result.stderr or result.stdout or "backup failed").strip()[-300:]
            )

    def create_store(self, slug: str) -> dict:
        if not SLUG_RE.fullmatch(slug or ""):
            raise BackupError("Invalid store slug.")
        self._run("backup-store", slug)
        rows = self.list_store(slug)
        if not rows:
            raise BackupError("Backup completed but no archive was found.")
        return rows[0]

    def create_platform(self) -> dict:
        self._run("backup-platform")
        rows = self.list_platform()
        if not rows:
            raise BackupError("Backup completed but no archive was found.")
        return rows[0]

    def list_store(self, slug: str) -> list[dict]:
        if not SLUG_RE.fullmatch(slug or ""):
            raise BackupError("Invalid store slug.")
        folder = ROOT / "stores" / slug
        if not folder.exists():
            return []
        rows = []
        for path in sorted(
            folder.glob(f"store_{slug}_*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            stamp = path.name[len(f"store_{slug}_") : -len(".tar.gz")]
            rows.append(
                {
                    "name": path.name,
                    "kind": "store",
                    "stamp": stamp,
                    "size": path.stat().st_size,
                    "dump": path.name,
                    "assets": None,
                }
            )
        return rows

    def list_platform(self) -> list[dict]:
        folder = ROOT / "full"
        if not folder.exists():
            return []
        rows = []
        for path in sorted(
            folder.glob("orionstore_full_*.dump"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            stamp = path.name[len("orionstore_full_") : -len(".dump")]
            assets = folder / f"shared_{stamp}.tar.gz"
            rows.append(
                {
                    "name": path.name,
                    "kind": "platform",
                    "stamp": stamp,
                    "size": path.stat().st_size
                    + (assets.stat().st_size if assets.exists() else 0),
                    "dump": path.name,
                    "assets": assets.name if assets.exists() else None,
                }
            )
        return rows

    def store_path(self, slug: str, name: str) -> Path:
        if not SLUG_RE.fullmatch(slug or "") or not NAME_RE.fullmatch(name or ""):
            raise BackupError("Invalid backup name.")
        path = ROOT / "stores" / slug / name
        if not path.is_file():
            raise BackupError("Backup not found.")
        return path

    def platform_path(self, name: str) -> Path:
        if not NAME_RE.fullmatch(name or ""):
            raise BackupError("Invalid backup name.")
        path = ROOT / "full" / name
        if not path.is_file():
            raise BackupError("Backup not found.")
        return path
