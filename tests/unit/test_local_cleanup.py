import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.upload.local_cleanup import LocalCleanupError


EXPECTED_FOLDER = "BaiduNetdisk:/screenshots/demo_app/demo_run"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_uploaded_confirmed_session(tmp_path) -> LocalRunSession:
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
    session.confirm_uploaded(confirmed_by="tester")
    (session.run_dir / "temp_video" / "sample.tmp").write_bytes(b"video")
    return session


def test_uploaded_confirmed_can_cleanup(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    record = session.cleanup_local_files()

    assert record["status"] == RunStatus.LOCAL_DELETED.value


def test_cleanup_writes_cleanup_record_json(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    record = session.cleanup_local_files()

    assert session.cleanup_record_path.is_file()
    assert json.loads(session.cleanup_record_path.read_text(encoding="utf-8")) == record


def test_cleanup_moves_status_to_local_deleted(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    session.cleanup_local_files()

    assert session.status == RunStatus.LOCAL_DELETED


def test_cleanup_deletes_allowed_directories(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    session.cleanup_local_files()

    for directory_name in ("fixed", "low", "high", "rejected", "temp_video"):
        assert not (session.run_dir / directory_name).exists()


def test_cleanup_keeps_required_files(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    session.cleanup_local_files()

    for file_name in (
        "summary.json",
        "meta.jsonl",
        "upload_manifest.json",
        "upload_record.json",
        "run.log",
    ):
        assert (session.run_dir / file_name).is_file()


def test_cleanup_fails_when_not_uploaded_confirmed(tmp_path):
    session = LocalRunSession(
        RunSessionConfig(root_dir=tmp_path, app_id="demo_app", run_id="demo_run")
    )
    session.start()

    with pytest.raises(LocalCleanupError, match="uploaded_confirmed"):
        session.cleanup_local_files()


def test_cleanup_fails_without_upload_manifest(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)
    session.upload_manifest_path.unlink()

    with pytest.raises(LocalCleanupError, match="upload_manifest.json"):
        session.cleanup_local_files()


def test_cleanup_fails_without_upload_record(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)
    session.upload_record_path.unlink()

    with pytest.raises(LocalCleanupError, match="upload_record.json"):
        session.cleanup_local_files()


def test_cleanup_fails_when_delete_allowed_is_false(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)
    record = json.loads(session.upload_record_path.read_text(encoding="utf-8"))
    record["delete_allowed"] = False
    session.upload_record_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(LocalCleanupError, match="delete_allowed"):
        session.cleanup_local_files()


def test_cleanup_does_not_enter_completed(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    session.cleanup_local_files()

    assert session.status != RunStatus.COMPLETED


def test_cleanup_writes_run_log_event(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    session.cleanup_local_files()

    events = read_jsonl(session.run_log_path)
    cleanup_events = [event for event in events if event["event"] == "local_deleted"]
    assert cleanup_events
    assert cleanup_events[-1]["status"] == RunStatus.LOCAL_DELETED.value


def test_repeated_cleanup_is_idempotent(tmp_path):
    session = make_uploaded_confirmed_session(tmp_path)

    first = session.cleanup_local_files()
    second = session.cleanup_local_files()

    assert first == second
    assert session.status == RunStatus.LOCAL_DELETED
    assert session.cleanup_record_path.is_file()
