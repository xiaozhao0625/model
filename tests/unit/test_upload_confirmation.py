import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.upload.upload_confirmation import (
    UploadConfirmationError,
)


EXPECTED_FOLDER = "BaiduNetdisk:/screenshots/demo_app/demo_run"
ACTUAL_FOLDER = "BaiduNetdisk:/screenshots/demo_app/demo_run_uploaded"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_upload_pending_session(tmp_path) -> LocalRunSession:
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
    session.evaluate_completion()
    session.generate_summary()
    session.generate_upload_manifest(EXPECTED_FOLDER)
    return session


def load_upload_record(session: LocalRunSession) -> dict:
    return json.loads(session.upload_record_path.read_text(encoding="utf-8"))


def test_upload_pending_can_confirm_uploaded(tmp_path):
    session = make_upload_pending_session(tmp_path)

    record = session.confirm_uploaded(
        actual_upload_folder=ACTUAL_FOLDER,
        confirmed_by="tester",
    )

    assert record["status"] == RunStatus.UPLOADED_CONFIRMED.value


def test_confirm_uploaded_writes_upload_record_json(tmp_path):
    session = make_upload_pending_session(tmp_path)

    record = session.confirm_uploaded(confirmed_by="tester")

    assert session.upload_record_path.is_file()
    assert load_upload_record(session) == record


def test_upload_record_fields_are_complete(tmp_path):
    session = make_upload_pending_session(tmp_path)

    record = session.confirm_uploaded(
        actual_upload_folder=ACTUAL_FOLDER,
        confirmed_by="tester",
    )

    assert set(record) == {
        "app_id",
        "run_id",
        "status",
        "local_path",
        "expected_upload_folder",
        "actual_upload_folder",
        "confirmed_by",
        "confirmed_at",
        "manifest_path",
        "valid_total",
        "fixed_count",
        "low_count",
        "high_count",
        "rejected_count",
        "delete_allowed",
    }
    assert record["app_id"] == "demo_app"
    assert record["run_id"] == "demo_run"
    assert record["local_path"] == str(session.run_dir)
    assert record["expected_upload_folder"] == EXPECTED_FOLDER
    assert record["actual_upload_folder"] == ACTUAL_FOLDER
    assert record["confirmed_by"] == "tester"
    assert record["manifest_path"] == str(session.upload_manifest_path)
    assert record["valid_total"] == 3
    assert record["fixed_count"] == 0
    assert record["low_count"] == 3
    assert record["high_count"] == 0
    assert record["rejected_count"] == 0
    assert record["delete_allowed"] is True
    assert isinstance(record["confirmed_at"], str)


def test_actual_upload_folder_defaults_to_expected_folder(tmp_path):
    session = make_upload_pending_session(tmp_path)

    record = session.confirm_uploaded(confirmed_by="tester")

    assert record["actual_upload_folder"] == EXPECTED_FOLDER


def test_confirm_uploaded_moves_status_to_uploaded_confirmed(tmp_path):
    session = make_upload_pending_session(tmp_path)

    session.confirm_uploaded(confirmed_by="tester")

    assert session.status == RunStatus.UPLOADED_CONFIRMED


def test_confirm_uploaded_fails_without_upload_manifest(tmp_path):
    session = LocalRunSession(
        RunSessionConfig(root_dir=tmp_path, app_id="demo_app", run_id="demo_run")
    )
    session.start()
    session.status = RunStatus.UPLOAD_PENDING

    with pytest.raises(UploadConfirmationError, match="upload_manifest.json"):
        session.confirm_uploaded(confirmed_by="tester")


def test_confirm_uploaded_fails_when_not_upload_pending(tmp_path):
    session = LocalRunSession(
        RunSessionConfig(root_dir=tmp_path, app_id="demo_app", run_id="demo_run")
    )
    session.start()
    session.upload_manifest_path.write_text(
        json.dumps(
            {
                "app_id": "demo_app",
                "run_id": "demo_run",
                "local_path": str(session.run_dir),
                "expected_upload_folder": EXPECTED_FOLDER,
                "valid_total": 0,
                "fixed_count": 0,
                "low_count": 0,
                "high_count": 0,
                "rejected_count": 0,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(UploadConfirmationError, match="upload_pending"):
        session.confirm_uploaded(confirmed_by="tester")


def test_confirm_uploaded_preserves_bucket_and_temp_directories(tmp_path):
    session = make_upload_pending_session(tmp_path)

    session.confirm_uploaded(confirmed_by="tester")

    for directory_name in ("fixed", "low", "high", "rejected", "temp_video"):
        assert (session.run_dir / directory_name).is_dir()


def test_confirm_uploaded_preserves_upload_manifest(tmp_path):
    session = make_upload_pending_session(tmp_path)

    session.confirm_uploaded(confirmed_by="tester")

    assert session.upload_manifest_path.is_file()


def test_confirm_uploaded_does_not_enter_local_deleted_or_completed(tmp_path):
    session = make_upload_pending_session(tmp_path)

    session.confirm_uploaded(confirmed_by="tester")

    assert session.status != RunStatus.LOCAL_DELETED
    assert session.status != RunStatus.COMPLETED


def test_confirm_uploaded_writes_run_log_event(tmp_path):
    session = make_upload_pending_session(tmp_path)

    session.confirm_uploaded(
        actual_upload_folder=ACTUAL_FOLDER,
        confirmed_by="tester",
    )

    events = read_jsonl(session.run_log_path)
    upload_events = [event for event in events if event["event"] == "upload_confirmed"]
    assert upload_events
    assert upload_events[-1]["status"] == RunStatus.UPLOADED_CONFIRMED.value
    assert upload_events[-1]["details"]["confirmed_by"] == "tester"
    assert upload_events[-1]["details"]["actual_upload_folder"] == ACTUAL_FOLDER
