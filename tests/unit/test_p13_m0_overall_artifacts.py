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


def test_p13_m0_overall_artifacts_exist():
    assert (P13_DIR / "p13_m0_overall_check.ps1").exists()
    assert (P13_DIR / "p13_m0_overall_check.py").exists()
    assert (REPO_ROOT / "docs/deployment/p13_m0_overall_check_quick_start.md").exists()
    assert (REPO_ROOT / "docs/deployment/p13_two_script_workflow.md").exists()


def test_p13_m0_overall_scripts_do_not_print_secrets():
    combined = "\n".join(
        read_text(path)
        for path in [
            P13_DIR / "p13_m0_overall_check.ps1",
            P13_DIR / "p13_m0_overall_check.py",
        ]
    )
    assert "DATABASE_URL=" not in combined
    assert "password@" not in combined.lower()
    assert "secret" not in combined.lower()


def test_p13_m0_overall_outputs_required_schema(tmp_path):
    result = run_script(
        "scripts/deploy/p13/p13_m0_overall_check.py",
        "--skip-network",
        "--skip-smoke",
        "--output-dir",
        str(tmp_path),
        "--master-url",
        "http://127.0.0.1:1",
        "--timeout",
        "0.1",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "blocking_errors" in payload
    assert "warnings" in payload
    assert "next_actions" in payload
    assert payload["machines"]["m0"]["ip"] == "192.168.1.18"
    assert payload["machines"]["w1"]["ip"] == "192.168.1.19"
    assert payload["machines"]["w2"]["ip"] == "192.168.1.20"
    assert payload["machines"]["w3"]["ip"] == "192.168.1.21"
    assert (tmp_path / "overall_summary.json").exists()
    assert (tmp_path / "overall_error_report.txt").exists()
    assert (tmp_path / "p13_overall_diagnostics.zip").exists()


def test_p13_two_script_workflow_is_short_and_actionable():
    text = read_text(REPO_ROOT / "docs/deployment/p13_two_script_workflow.md")
    assert "p13_env_preflight.ps1" in text
    assert "p13_m0_overall_check.ps1" in text
    assert "overall_summary.json" in text
