import json
import subprocess
import sys
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus


REPO_ROOT = Path(__file__).resolve().parents[2]
P4_DRY_RUN_SCRIPT = REPO_ROOT / "scripts" / "dev" / "mock_p4_workers_run.py"


def run_dry_run(tmp_path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(P4_DRY_RUN_SCRIPT),
            "--root",
            str(tmp_path),
            "--target-min",
            "3",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_p4_dry_run_outputs_valid_json(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["workers"] == [
        "pc_game_behavior",
        "pc_game_stub",
        "pc_app_stub",
        "web_stub",
        "android_stub",
    ]


def test_pc_game_behavior_reaches_capture_completed_and_high_bucket(tmp_path):
    output = run_dry_run(tmp_path)

    assert (
        output["final_status_by_worker"]["pc_game_behavior"]
        == RunStatus.CAPTURE_COMPLETED.value
    )
    assert output["bucket_counts_by_worker"]["pc_game_behavior"]["high_count"] > 0


def test_pc_game_behavior_generates_behavior_actions_jsonl(tmp_path):
    output = run_dry_run(tmp_path)

    path = Path(output["generated_files"]["pc_game_behavior"]["behavior_actions"])

    assert path.is_file()


def test_pc_game_stub_reaches_capture_completed_and_high_bucket(tmp_path):
    output = run_dry_run(tmp_path)

    assert (
        output["final_status_by_worker"]["pc_game_stub"]
        == RunStatus.CAPTURE_COMPLETED.value
    )
    assert output["bucket_counts_by_worker"]["pc_game_stub"]["high_count"] > 0


def test_pc_app_stub_reaches_capture_completed_and_low_bucket(tmp_path):
    output = run_dry_run(tmp_path)

    assert (
        output["final_status_by_worker"]["pc_app_stub"]
        == RunStatus.CAPTURE_COMPLETED.value
    )
    assert output["bucket_counts_by_worker"]["pc_app_stub"]["low_count"] > 0


def test_web_stub_reaches_capture_completed_and_low_bucket(tmp_path):
    output = run_dry_run(tmp_path)

    assert (
        output["final_status_by_worker"]["web_stub"]
        == RunStatus.CAPTURE_COMPLETED.value
    )
    assert output["bucket_counts_by_worker"]["web_stub"]["low_count"] > 0


def test_web_stub_content_area_only_is_true(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["content_area_only_for_web"] is True


def test_android_stub_reaches_capture_completed_and_low_bucket(tmp_path):
    output = run_dry_run(tmp_path)

    assert (
        output["final_status_by_worker"]["android_stub"]
        == RunStatus.CAPTURE_COMPLETED.value
    )
    assert output["bucket_counts_by_worker"]["android_stub"]["low_count"] > 0


def test_all_runs_have_required_files_and_no_upload_manifest(tmp_path):
    output = run_dry_run(tmp_path)

    for worker_name in output["workers"]:
        files = output["generated_files"][worker_name]
        assert Path(files["summary"]).is_file()
        assert Path(files["meta"]).is_file()
        assert Path(files["run_log"]).is_file()
        assert output["forbidden_files_absent"][worker_name]["upload_manifest"] is True


def test_all_runs_do_not_enter_completed(tmp_path):
    output = run_dry_run(tmp_path)

    assert all(
        status != RunStatus.COMPLETED.value
        for status in output["final_status_by_worker"].values()
    )


def test_dry_run_script_does_not_import_real_execution_libraries():
    source = P4_DRY_RUN_SCRIPT.read_text(encoding="utf-8")
    forbidden_imports = [
        "import obs",
        "import ffmpeg",
        "import adb",
        "import appium",
        "import airtest",
        "import playwright",
        "import pywinauto",
        "import pydirectinput",
        "import paddleocr",
        "import easyocr",
        "import subprocess",
        "from subprocess",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source
