from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
P13_DIR = REPO_ROOT / "scripts" / "deploy" / "p13"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_p13_env_preflight_artifacts_exist():
    assert (P13_DIR / "p13_env_preflight.ps1").exists()
    assert (P13_DIR / "p13_env_preflight.py").exists()
    assert (P13_DIR / "p13_install_hints.py").exists()
    assert (P13_DIR / "p13_report_uploader.py").exists()
    assert (REPO_ROOT / "configs/deploy/p13_software_requirements.example.json").exists()
    assert (REPO_ROOT / "docs/deployment/p13_env_preflight_quick_start.md").exists()


def test_p13_env_preflight_scripts_do_not_print_secrets():
    combined = "\n".join(
        read_text(path)
        for path in [
            P13_DIR / "p13_env_preflight.ps1",
            P13_DIR / "p13_env_preflight.py",
            P13_DIR / "p13_report_uploader.py",
        ]
    )
    assert "DATABASE_URL=" not in combined
    assert "password@" not in combined.lower()
    assert "secret" not in combined.lower()


def test_p13_software_requirements_include_fixed_topology_ips():
    payload = json.loads(
        read_text(REPO_ROOT / "configs/deploy/p13_software_requirements.example.json")
    )
    ips = {machine["ip"] for machine in payload["topology"]["machines"].values()}
    assert {"192.168.1.18", "192.168.1.19", "192.168.1.20", "192.168.1.21"} <= ips


def test_p13_env_preflight_outputs_required_schema(tmp_path):
    result = run_script(
        "scripts/deploy/p13/p13_env_preflight.py",
        "--role",
        "W2",
        "--output-dir",
        str(tmp_path),
        "--master-url",
        "http://127.0.0.1:1",
        "--timeout",
        "0.1",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["role"] == "W2"
    assert payload["ip"] == "192.168.1.20"
    assert "status" in payload
    assert "checks" in payload
    assert "next_step" in payload
    assert "safe_to_continue" in payload
    assert (tmp_path / "W2" / "preflight_report.json").exists()
    assert (tmp_path / "W2" / "preflight_summary.txt").exists()
    assert list((tmp_path / "W2").glob("diagnostics_W2_*.zip"))
