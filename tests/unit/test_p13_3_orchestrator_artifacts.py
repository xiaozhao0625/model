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
    browser = next(item for item in catalog if item["name"] == "browser_chromium_or_edge")
    assert browser["install_policy"] == "detect_only"
    assert "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe" in browser["candidate_paths"]
    assert any("App Paths\\msedge.exe" in path for path in browser["registry_app_paths"])
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
            assert config["ssh_user"] == "Administrator"
            assert config["project_root"] == "D:\\work\\model"


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


def test_p13_4_2_execute_requires_allow_tools():
    install_script = (REPO_ROOT / "scripts/p13/02_install_role.ps1").read_text(encoding="utf-8")
    install_lib = (REPO_ROOT / "scripts/p13/lib/Install-Tool.ps1").read_text(encoding="utf-8")
    assert "Execute mode requires -AllowTools whitelist." in install_script
    assert "Skipped because tool is not in AllowTools whitelist." in install_script
    assert "Installation blocked by policy." in install_lib


def test_p13_4_2_1_installer_backend_hardening_artifacts():
    install_script = (REPO_ROOT / "scripts/p13/02_install_role.ps1").read_text(encoding="utf-8")
    install_lib = (REPO_ROOT / "scripts/p13/lib/Install-Tool.ps1").read_text(encoding="utf-8")
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    manifest = json.loads((REPO_ROOT / "deploy/installers/manifest.example.json").read_text(encoding="utf-8"))

    assert "InstallBackend" in install_script
    assert "Resolve-Winget" in install_lib
    assert "Invoke-StagedInstallStep" in install_lib
    assert "installer_missing" in install_lib
    assert "sha256_mismatch" in install_lib
    assert "/deploy/installers/*" in gitignore
    assert "!/deploy/installers/manifest.example.json" in gitignore
    assert set(manifest) >= {"git", "python", "ffmpeg", "adb"}
    assert manifest["git"]["allowed_roles"] == ["W1", "W2", "W3"]
