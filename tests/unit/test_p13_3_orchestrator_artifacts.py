from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_p13_3_catalog_and_roles_are_complete():
    catalog = json.loads((REPO_ROOT / "deploy/software_catalog.json").read_text(encoding="utf-8"))
    matrix = json.loads((REPO_ROOT / "deploy/role_matrix.json").read_text(encoding="utf-8"))

    required_catalog_fields = {"name", "roles", "required", "detect_commands", "install_hint"}
    names = {item["name"] for item in catalog}
    assert {"python", "git", "nodejs", "postgresql", "redis", "nvidia_driver", "obs", "ffmpeg", "playwright", "adb"} <= names
    assert all(required_catalog_fields <= set(item) for item in catalog)
    postgresql = next(item for item in catalog if item["name"] == "postgresql")
    assert postgresql["candidate_paths"][0] == "E:\\work\\pgsql\\bin\\psql.exe"
    assert {"M0", "W1", "W2", "W3"} == set(matrix["roles"])

    for role, config in matrix["roles"].items():
        assert config["role"] == role
        for field in [
            "name",
            "host",
            "ip",
            "gpu_expectation",
            "required_tools",
            "optional_tools",
            "required_services",
            "preferred_services",
            "ports",
            "project_modules",
            "env_template_keys",
            "master_api_url",
            "notes",
        ]:
            assert field in config
        if role != "M0":
            assert "postgresql" not in config["required_tools"]
            assert "DATABASE_URL" not in config["env_template_keys"]


def test_p13_3_powershell_scripts_parse():
    scripts = list((REPO_ROOT / "scripts/p13").glob("*.ps1")) + list((REPO_ROOT / "scripts/p13/lib").glob("*.ps1"))
    assert scripts
    for script in scripts:
        command = (
            "$errors=$null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile('{script}', [ref]$null, [ref]$errors) | Out-Null; "
            "if ($errors.Count -gt 0) { $errors | ForEach-Object { $_.ToString() }; exit 1 }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{script} failed parser check: {result.stdout}\n{result.stderr}"


def test_p13_3_plan_mode_has_no_execute_side_effect_language():
    install_lib = (REPO_ROOT / "scripts/p13/lib/Install-Tool.ps1").read_text(encoding="utf-8")
    assert "Plan mode only; no installation executed." in install_lib
    assert "-Mode', 'Plan'" in (REPO_ROOT / "scripts/p13/m0_orchestrator.ps1").read_text(encoding="utf-8")


def test_p13_3_sensitive_terms_are_redacted_by_safe_json():
    script = REPO_ROOT / "scripts/p13/lib/ConvertTo-SafeJson.ps1"
    command = (
        f". '{script}'; "
        "$payload = @{ password='secret'; api_key='abc'; DATABASE_URL='postgresql://u:p@h/db'; normal='ok' }; "
        "$payload | ConvertTo-SafeJson -Depth 4"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "secret" not in result.stdout
    assert "abc" not in result.stdout
    assert "postgresql://u:p@h/db" not in result.stdout
    assert "ok" in result.stdout


def test_p13_3_remote_unreachable_is_reported_not_crashed():
    orchestrator = (REPO_ROOT / "scripts/p13/m0_orchestrator.ps1").read_text(encoding="utf-8")
    assert "remote_unreachable" in orchestrator
    assert "Enable OpenSSH Server" in orchestrator


def test_p13_3_postgresql_partial_detection_is_explainable():
    detector = (REPO_ROOT / "scripts/p13/lib/Detect-Tool.ps1").read_text(encoding="utf-8")
    installer = (REPO_ROOT / "scripts/p13/lib/Install-Tool.ps1").read_text(encoding="utf-8")
    assert "PostgreSQL port is reachable but psql client was not found" in detector
    assert "add PostgreSQL bin to PATH or configure known path" in detector
    assert "already_available" in installer
