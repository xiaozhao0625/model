from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_p13_health_script_help_is_available():
    result = run_script("scripts/deploy/p13/check_m0_master_stack.py", "--help")
    assert result.returncode == 0
    assert "P13 M0 Master" in result.stdout


def test_p13_health_script_outputs_required_json_shape():
    result = run_script(
        "scripts/deploy/p13/check_w1_pc_game_stack.py",
        "--master-url",
        "http://127.0.0.1:1",
        "--timeout",
        "0.1",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["role"] == "pc_game_worker"
    assert "checks" in payload
    assert "available" in payload
    assert "unavailable" in payload
    assert payload["real_capture_started"] is False


def test_p13_collect_diagnostics_excludes_env_file(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    (source / ".env").write_text("DATABASE_URL=postgresql://user:secret@host/db", encoding="utf-8")
    (source / "run.log").write_text('{"event":"ok"}\n', encoding="utf-8")

    result = run_script(
        "scripts/deploy/p13/collect_diagnostics.py",
        "--machine",
        "M0",
        "--source",
        str(source),
        "--output",
        str(output),
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    zip_path = Path(payload["zip_path"])
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    assert "run.log" in names
    assert ".env" not in names
    assert "diagnostics_manifest.json" in names
