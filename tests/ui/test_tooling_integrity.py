"""Guardrails for the verification tooling itself (no application code involved)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _load(module_name: str, filename: str):
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_file_length_limits_come_from_pyproject() -> None:
    mod = _load("_tooling_file_length", "check_file_length.py")
    config = mod._load_config()

    assert config["default_max"] == 500
    limits = {entry["glob"]: entry["max"] for entry in config["paths"]}
    assert limits["**/*_service.py"] == 400
    assert limits["05-API/v1/*.py"] == 300
    assert limits["03-MODELS/**/*.py"] == 250
    assert limits["migrations/versions/*.py"] == 200
    # Explicit, documented legacy exceptions live in pyproject.toml.
    assert len(limits) >= 10
    assert mod._max_for("04-SERVICES/auth/auth_service.py", config) == 400
    assert mod._max_for("05-API/v1/products.py", config) == 300
    assert mod._max_for("03-MODELS/user/user.py", config) == 250
    assert mod._max_for("migrations/versions/0001.py", config) == 200
    # Legacy exceptions are explicitly declared (not hidden in the script).
    assert mod._max_for("tests/api/test_v2_api.py", config) == limits[
        "tests/api/test_v2_api.py"
    ]
    assert mod._max_for(
        "03-MODELS/subscription/subscription.py", config
    ) == limits["03-MODELS/subscription/subscription.py"]


def test_file_length_reports_violations(tmp_path: Path, monkeypatch) -> None:
    mod = _load("_tooling_file_length_fail", "check_file_length.py")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.orion.file_length]\ndefault_max = 3\npaths = []\n", encoding="utf-8"
    )
    (tmp_path / "too_long.py").write_text("x\ny\nz\nw\n", encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "PYPROJECT", tmp_path / "pyproject.toml")

    assert mod.main() == 1


def test_coverage_path_defaults() -> None:
    mod = _load("_tooling_coverage", "check_coverage.py")
    manifest = {
        "path_defaults": {"04-SERVICES/": 80, "05-API/": 70},
        "files": {"04-SERVICES/auth/auth_service.py": {"wave": 1, "min": 90}},
    }

    assert mod._min_for_file("04-SERVICES/auth/auth_service.py", manifest) == 90
    assert mod._min_for_file("04-SERVICES/other/new.py", manifest) == 80
    assert mod._min_for_file("05-API/v1/new.py", manifest) == 70
    assert mod._min_for_file("unknown/new.py", manifest) is None


def test_coverage_main_lists_untracked_without_error(
    tmp_path: Path, monkeypatch
) -> None:
    mod = _load("_tooling_coverage_main", "check_coverage.py")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    source = tmp_path / "04-SERVICES" / "new_feature"
    source.mkdir(parents=True)
    (source / "service.py").write_text("value = 1\n", encoding="utf-8")

    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        "version: 1\npath_defaults:\n  '04-SERVICES/': 80\nfiles: {}\n"
        "exclude_from_scan: []\npr_modified_min: 80\n",
        encoding="utf-8",
    )
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    "04-SERVICES/new_feature/service.py": {
                        "summary": {"percent_covered": 95.0}
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_coverage.py",
            "--coverage-json",
            str(coverage_path),
            "--manifest",
            str(manifest_path),
        ],
    )

    assert mod.main() == 0


def test_migrations_check_is_read_only_and_fails_loudly() -> None:
    source = (SCRIPTS / "check_migrations.py").read_text(encoding="utf-8")

    assert "command.revision" not in source
    assert "autogenerate=True" not in source
    assert "compare_metadata" in source
    assert "sys.exit(main())" in source
    assert "return 1" in source


def test_ci_declares_reproducible_gates() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for needle in (
        "npm ci",
        "npm run build:css",
        "git diff --exit-code",
        "python scripts/check_migrations.py",
        "continue-on-error: true",
        "pytest -v -m e2e",
        "e2e-screenshots",
    ):
        assert needle in ci


def test_playwright_is_pinned() -> None:
    lines = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()

    assert "playwright==1.62.0" in lines
