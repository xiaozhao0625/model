import json
import subprocess
import sys
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus


REPO_ROOT = Path(__file__).resolve().parents[2]
P5_DRY_RUN_SCRIPT = REPO_ROOT / "scripts" / "dev" / "mock_p5_recovery_run.py"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def run_dry_run(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(P5_DRY_RUN_SCRIPT),
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


def test_p5_dry_run_manual_seed_success_reaches_capture_completed(tmp_path):
    output = run_dry_run(tmp_path)

    assert (
        output["final_status_by_scenario"]["manual_seed_success"]
        == RunStatus.CAPTURE_COMPLETED.value
    )


def test_p5_dry_run_failed_low_yield_reaches_failed_low_yield(tmp_path):
    output = run_dry_run(tmp_path)

    assert (
        output["final_status_by_scenario"]["failed_low_yield"]
        == RunStatus.FAILED_LOW_YIELD.value
    )


def test_p5_dry_run_does_not_generate_upload_manifest(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["upload_manifest_absent"]["manual_seed_success"] is True
    assert output["upload_manifest_absent"]["failed_low_yield"] is True


def test_p5_dry_run_does_not_enter_completed(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["completed_absent"]["manual_seed_success"] is True
    assert output["completed_absent"]["failed_low_yield"] is True


def test_manual_seed_record_and_run_log_are_valid_jsonl(tmp_path):
    output = run_dry_run(tmp_path)

    for scenario in output["scenarios"]:
        manual_records = read_jsonl(Path(output["manual_seed_record_path"][scenario]))
        run_log_records = read_jsonl(Path(output["run_log_path"][scenario]))

        assert manual_records
        assert run_log_records
        assert "manual_seed_requested" in [
            record["event"] for record in manual_records
        ]
        assert "manual_seed_completed" in [
            record["event"] for record in manual_records
        ]


def test_p5_dry_run_outputs_expected_valid_totals(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["valid_total_by_scenario"]["manual_seed_success"] == 3
    assert output["valid_total_by_scenario"]["failed_low_yield"] == 2
