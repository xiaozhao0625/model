import json
import subprocess
import sys
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def run_mock_script(tmp_path, unique_count=3, duplicate_count=1):
    script = Path("scripts/dev/mock_local_run.py")
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(tmp_path),
            "--app-id",
            "demo_app",
            "--run-id",
            "demo_run",
            "--target-min",
            "3",
            "--unique-count",
            str(unique_count),
            "--duplicate-count",
            str(duplicate_count),
            "--bucket",
            "low",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_mock_dry_run_reaches_capture_completed_with_small_target(tmp_path):
    output = run_mock_script(tmp_path)

    assert output["final_status"] == RunStatus.CAPTURE_COMPLETED.value


def test_duplicate_count_does_not_increase_valid_total(tmp_path):
    output = run_mock_script(tmp_path, unique_count=3, duplicate_count=5)

    assert output["valid_total"] == 3
    assert output["low_count"] == 3


def test_summary_json_exists_and_has_expected_counts(tmp_path):
    output = run_mock_script(tmp_path)

    summary_path = Path(output["summary_path"])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["app_id"] == "demo_app"
    assert summary["run_id"] == "demo_run"
    assert summary["fixed_count"] == 0
    assert summary["low_count"] == 3
    assert summary["high_count"] == 0
    assert summary["rejected_count"] == 0
    assert summary["valid_total"] == 3


def test_meta_jsonl_exists_and_has_effective_rows_only(tmp_path):
    output = run_mock_script(tmp_path)

    records = read_jsonl(Path(output["meta_path"]))
    assert len(records) == 3
    assert all(record["valid"] is True for record in records)


def test_run_log_contains_key_events(tmp_path):
    output = run_mock_script(tmp_path)

    events = [record["event"] for record in read_jsonl(Path(output["run_log_path"]))]
    assert "session_started" in events
    assert "image_saved" in events
    assert "duplicate_rejected" in events
    assert "capture_completed" in events


def test_upload_manifest_is_not_created(tmp_path):
    output = run_mock_script(tmp_path)

    assert not (Path(output["run_dir"]) / "upload_manifest.json").exists()


def test_final_status_is_not_completed_or_upload_pending(tmp_path):
    output = run_mock_script(tmp_path)

    assert output["final_status"] != RunStatus.COMPLETED.value
    assert output["final_status"] != RunStatus.UPLOAD_PENDING.value
