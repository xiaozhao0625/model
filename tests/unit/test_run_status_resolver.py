import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.runtime.run_status_resolver import (
    RunStatusResolveError,
    RunStatusResolver,
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_summary(
    run_dir: Path,
    fixed_count: int = 0,
    low_count: int = 1000,
    high_count: int = 0,
    rejected_count: int = 0,
) -> None:
    write_json(
        run_dir / "summary.json",
        {
            "app_id": "demo_app",
            "run_id": "demo_run",
            "fixed_count": fixed_count,
            "low_count": low_count,
            "high_count": high_count,
            "rejected_count": rejected_count,
            "valid_total": fixed_count + low_count + high_count,
        },
    )


def write_run_log(run_dir: Path, events: list[str]) -> None:
    lines = []
    for event in events:
        lines.append(
            json.dumps(
                {
                    "timestamp": "2026-06-13T00:00:00+00:00",
                    "app_id": "demo_app",
                    "run_id": "demo_run",
                    "event": event,
                    "status": event,
                    "details": {},
                },
                sort_keys=True,
            )
        )
    (run_dir / "run.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_resolves_capture_completed_when_only_summary_is_complete(tmp_path):
    write_summary(tmp_path)

    assert RunStatusResolver().resolve(tmp_path) == RunStatus.CAPTURE_COMPLETED


def test_resolves_upload_pending_when_upload_manifest_exists(tmp_path):
    write_summary(tmp_path)
    write_json(tmp_path / "upload_manifest.json", {"status": "upload_pending"})

    assert RunStatusResolver().resolve(tmp_path) == RunStatus.UPLOAD_PENDING


def test_resolves_uploaded_confirmed_when_upload_record_exists(tmp_path):
    write_summary(tmp_path)
    write_json(tmp_path / "upload_manifest.json", {"status": "upload_pending"})
    write_json(tmp_path / "upload_record.json", {"status": "uploaded_confirmed"})

    assert RunStatusResolver().resolve(tmp_path) == RunStatus.UPLOADED_CONFIRMED


def test_resolves_local_deleted_when_cleanup_record_exists(tmp_path):
    write_summary(tmp_path)
    write_json(tmp_path / "upload_manifest.json", {"status": "upload_pending"})
    write_json(tmp_path / "upload_record.json", {"status": "uploaded_confirmed"})
    write_json(tmp_path / "cleanup_record.json", {"status": "local_deleted"})

    assert RunStatusResolver().resolve(tmp_path) == RunStatus.LOCAL_DELETED


def test_resolves_completed_when_run_log_has_completed_event(tmp_path):
    write_summary(tmp_path)
    write_json(tmp_path / "cleanup_record.json", {"status": "local_deleted"})
    write_run_log(tmp_path, ["session_started", "completed"])

    assert RunStatusResolver().resolve(tmp_path) == RunStatus.COMPLETED


def test_resolves_highest_priority_when_multiple_artifacts_exist(tmp_path):
    write_summary(tmp_path)
    write_json(tmp_path / "upload_manifest.json", {"status": "upload_pending"})
    write_json(tmp_path / "upload_record.json", {"status": "uploaded_confirmed"})
    write_json(tmp_path / "cleanup_record.json", {"status": "local_deleted"})
    write_run_log(tmp_path, ["completed"])

    assert RunStatusResolver().resolve(tmp_path) == RunStatus.COMPLETED


def test_empty_run_directory_resolves_running(tmp_path):
    assert RunStatusResolver().resolve(tmp_path) == RunStatus.RUNNING


def test_invalid_run_log_json_line_raises_clear_error(tmp_path):
    (tmp_path / "run.log").write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(RunStatusResolveError, match="invalid JSON in run.log"):
        RunStatusResolver().resolve(tmp_path)


def test_cleanup_completed_is_not_a_run_status():
    assert "cleanup_completed" not in {status.value for status in RunStatus}


def test_completed_max_is_not_a_run_status():
    assert "completed_max" not in {status.value for status in RunStatus}


def test_local_run_session_can_restore_status_from_existing_artifacts(tmp_path):
    session = LocalRunSession(
        RunSessionConfig(root_dir=tmp_path, app_id="demo_app", run_id="demo_run")
    )
    write_summary(session.run_dir)
    write_json(session.upload_manifest_path, {"status": "upload_pending"})

    restored_status = session.restore_status()

    assert restored_status == RunStatus.UPLOAD_PENDING
    assert session.status == RunStatus.UPLOAD_PENDING
