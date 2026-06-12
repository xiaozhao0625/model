import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.upload.upload_manifest import (
    UploadManifestError,
    UploadManifestGenerator,
)


EXPECTED_FOLDER = "BaiduNetdisk:/screenshots/demo_app/demo_run"


def make_completed_session(tmp_path) -> LocalRunSession:
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
    return session


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_capture_completed_can_generate_upload_manifest(tmp_path):
    session = make_completed_session(tmp_path)

    manifest = session.generate_upload_manifest(EXPECTED_FOLDER)

    assert session.upload_manifest_path.is_file()
    assert manifest["status"] == RunStatus.UPLOAD_PENDING.value


def test_manifest_generation_fails_before_capture_completed(tmp_path):
    session = LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="demo_app",
            run_id="demo_run",
            target_min=3,
        )
    )
    session.start()
    session.save_image(Bucket.LOW, b"low")
    session.generate_summary()

    with pytest.raises(UploadManifestError, match="capture_completed"):
        session.generate_upload_manifest(EXPECTED_FOLDER)


def test_manifest_generation_fails_without_summary_json(tmp_path):
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

    with pytest.raises(UploadManifestError, match="summary.json"):
        session.generate_upload_manifest(EXPECTED_FOLDER)


def test_manifest_counts_match_summary_json(tmp_path):
    session = make_completed_session(tmp_path)
    summary = session.generate_summary()

    manifest = session.generate_upload_manifest(EXPECTED_FOLDER)

    for field in (
        "valid_total",
        "fixed_count",
        "low_count",
        "high_count",
        "rejected_count",
    ):
        assert manifest[field] == summary[field]


def test_manifest_contains_expected_upload_folder(tmp_path):
    session = make_completed_session(tmp_path)

    manifest = session.generate_upload_manifest(EXPECTED_FOLDER)

    assert manifest["expected_upload_folder"] == EXPECTED_FOLDER


def test_manifest_contains_file_count_and_total_bytes(tmp_path):
    session = make_completed_session(tmp_path)

    manifest = session.generate_upload_manifest(EXPECTED_FOLDER)

    assert manifest["file_count"] >= 1
    assert manifest["total_bytes"] > 0


def test_manifest_generation_moves_status_to_upload_pending(tmp_path):
    session = make_completed_session(tmp_path)

    session.generate_upload_manifest(EXPECTED_FOLDER)

    assert session.status == RunStatus.UPLOAD_PENDING


def test_manifest_generation_does_not_advance_past_upload_pending(tmp_path):
    session = make_completed_session(tmp_path)

    session.generate_upload_manifest(EXPECTED_FOLDER)

    assert session.status != RunStatus.UPLOADED_CONFIRMED
    assert session.status != RunStatus.LOCAL_DELETED
    assert session.status != RunStatus.COMPLETED


def test_manifest_generation_preserves_bucket_and_temp_directories(tmp_path):
    session = make_completed_session(tmp_path)
    expected_dirs = ["fixed", "low", "high", "rejected", "temp_video"]

    session.generate_upload_manifest(EXPECTED_FOLDER)

    for directory_name in expected_dirs:
        assert (session.run_dir / directory_name).is_dir()


def test_manifest_is_written_to_run_dir(tmp_path):
    session = make_completed_session(tmp_path)

    manifest = session.generate_upload_manifest(EXPECTED_FOLDER)
    written = load_manifest(session.upload_manifest_path)

    assert written == manifest
    assert written["local_path"] == str(session.run_dir)


def test_generator_rejects_non_capture_completed_status(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text("{}", encoding="utf-8")

    with pytest.raises(UploadManifestError, match="capture_completed"):
        UploadManifestGenerator().generate(
            run_dir=run_dir,
            expected_upload_folder=EXPECTED_FOLDER,
            current_status=RunStatus.RUNNING,
        )
