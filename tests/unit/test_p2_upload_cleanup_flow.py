import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_lifecycle import RunTransitionError
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)


EXPECTED_FOLDER = "BaiduNetdisk:/screenshots/demo_app/demo_run"
REPO_ROOT = Path(__file__).resolve().parents[2]
P2_DRY_RUN_SCRIPT = REPO_ROOT / "scripts" / "dev" / "mock_upload_cleanup_run.py"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_capture_completed_session(tmp_path) -> LocalRunSession:
    session = LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="demo_app",
            run_id="demo_run",
            target_min=3,
        )
    )
    session.start()
    for index in range(3):
        session.save_image(Bucket.LOW, f"low-{index}".encode())
    session.save_image(Bucket.LOW, b"low-0")
    session.evaluate_completion()
    session.generate_summary()
    return session


def make_local_deleted_session(tmp_path) -> LocalRunSession:
    session = make_capture_completed_session(tmp_path)
    session.generate_upload_manifest(EXPECTED_FOLDER)
    session.confirm_uploaded(confirmed_by="tester")
    (session.run_dir / "temp_video" / "sample.tmp").write_bytes(b"video")
    session.cleanup_local_files()
    return session


def run_p2_dry_run(tmp_path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(P2_DRY_RUN_SCRIPT),
            "--root",
            str(tmp_path),
            "--app-id",
            "demo_app",
            "--run-id",
            "demo_run",
            "--target-min",
            "3",
            "--unique-count",
            "3",
            "--duplicate-count",
            "1",
            "--bucket",
            "low",
            "--confirmed-by",
            "tester",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_p2_dry_run_finishes_as_completed(tmp_path):
    output = run_p2_dry_run(tmp_path)

    assert output["final_status"] == RunStatus.COMPLETED.value


def test_finalize_completed_can_only_run_from_local_deleted(tmp_path):
    session = make_local_deleted_session(tmp_path)

    status = session.finalize_completed()

    assert status == RunStatus.COMPLETED
    assert session.status == RunStatus.COMPLETED


def test_finalize_completed_fails_before_local_deleted(tmp_path):
    session = make_capture_completed_session(tmp_path)

    with pytest.raises(RunTransitionError, match="capture_completed -> completed"):
        session.finalize_completed()


def test_p2_dry_run_writes_upload_manifest_record_and_cleanup_record(tmp_path):
    output = run_p2_dry_run(tmp_path)

    assert Path(output["manifest_path"]).is_file()
    assert Path(output["upload_record_path"]).is_file()
    assert Path(output["cleanup_record_path"]).is_file()


def test_p2_dry_run_deletes_only_large_capture_directories(tmp_path):
    output = run_p2_dry_run(tmp_path)
    run_dir = Path(output["local_path"])

    for directory_name in ("fixed", "low", "high", "rejected", "temp_video"):
        assert not (run_dir / directory_name).exists()
    assert sorted(output["deleted_dirs"]) == [
        "fixed",
        "high",
        "low",
        "rejected",
        "temp_video",
    ]


def test_p2_dry_run_keeps_required_files(tmp_path):
    output = run_p2_dry_run(tmp_path)
    run_dir = Path(output["local_path"])

    for file_name in (
        "summary.json",
        "meta.jsonl",
        "upload_manifest.json",
        "upload_record.json",
        "cleanup_record.json",
        "run.log",
    ):
        assert (run_dir / file_name).is_file()
    assert sorted(output["kept_files"]) == [
        "cleanup_record.json",
        "meta.jsonl",
        "run.log",
        "summary.json",
        "upload_manifest.json",
        "upload_record.json",
    ]


def test_duplicate_images_do_not_pollute_valid_total(tmp_path):
    output = run_p2_dry_run(tmp_path)
    summary = read_json(Path(output["summary_path"]))

    assert output["valid_total"] == 3
    assert summary["valid_total"] == 3
    assert summary["low_count"] == 3


def test_p2_dry_run_run_log_contains_key_events(tmp_path):
    output = run_p2_dry_run(tmp_path)
    events = [entry["event"] for entry in read_jsonl(Path(output["run_log_path"]))]

    for event in (
        "session_started",
        "image_saved",
        "duplicate_rejected",
        "capture_completed",
        "upload_confirmed",
        "local_deleted",
        "completed",
    ):
        assert event in events
