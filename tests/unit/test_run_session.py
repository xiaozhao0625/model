import json

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_session(tmp_path, target_min=1000):
    return LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="demo_app",
            run_id="run_001",
            target_min=target_min,
        )
    )


def test_create_session_creates_run_directory(tmp_path):
    session = make_session(tmp_path)

    assert session.run_dir.is_dir()


def test_start_sets_status_to_running(tmp_path):
    session = make_session(tmp_path)

    session.start()

    assert session.status == RunStatus.RUNNING


def test_save_low_image_updates_summary(tmp_path):
    session = make_session(tmp_path)
    session.start()

    session.save_image(Bucket.LOW, b"low-image")
    summary = session.generate_summary()

    assert summary["low_count"] == 1
    assert summary["valid_total"] == 1


def test_duplicate_low_image_does_not_increase_valid_total(tmp_path):
    session = make_session(tmp_path)
    session.start()

    session.save_image(Bucket.LOW, b"same-image")
    session.save_image(Bucket.LOW, b"same-image")

    assert session.generate_summary()["valid_total"] == 1


def test_duplicate_rejected_event_is_written_to_run_log(tmp_path):
    session = make_session(tmp_path)
    session.start()

    first = session.save_image(Bucket.LOW, b"same-image")
    session.save_image(Bucket.LOW, b"same-image")
    events = read_jsonl(session.run_log_path)

    duplicate_events = [event for event in events if event["event"] == "duplicate_rejected"]
    assert duplicate_events
    assert duplicate_events[-1]["status"] == "running"
    assert duplicate_events[-1]["details"]["reason"] == "duplicate_content_hash"
    assert duplicate_events[-1]["details"]["duplicate_of"] == first.meta["image_id"]


def test_image_saved_event_is_written_to_run_log(tmp_path):
    session = make_session(tmp_path)
    session.start()

    result = session.save_image(Bucket.LOW, b"low-image")
    events = read_jsonl(session.run_log_path)

    image_events = [event for event in events if event["event"] == "image_saved"]
    assert image_events
    assert image_events[-1]["status"] == "running"
    assert image_events[-1]["details"]["image_id"] == result.meta["image_id"]
    assert image_events[-1]["details"]["bucket"] == "low"


def test_evaluate_completion_enters_capture_completed_with_small_target(tmp_path):
    session = make_session(tmp_path, target_min=3)
    session.start()

    for index in range(3):
        session.save_image(Bucket.LOW, f"low-{index}".encode())
    decision = session.evaluate_completion()

    assert decision.next_status == RunStatus.CAPTURE_COMPLETED
    assert session.status == RunStatus.CAPTURE_COMPLETED


def test_capture_completed_does_not_directly_enter_completed(tmp_path):
    session = make_session(tmp_path, target_min=3)
    session.start()

    for index in range(3):
        session.save_image(Bucket.LOW, f"low-{index}".encode())
    session.evaluate_completion()

    assert session.status == RunStatus.CAPTURE_COMPLETED
    assert session.status != RunStatus.COMPLETED


def test_run_log_is_valid_jsonl(tmp_path):
    session = make_session(tmp_path, target_min=1)
    session.start()
    session.save_image(Bucket.LOW, b"low-image")
    session.evaluate_completion()

    events = read_jsonl(session.run_log_path)
    assert events
    for event in events:
        assert set(event) == {
            "timestamp",
            "app_id",
            "run_id",
            "event",
            "status",
            "details",
        }
        assert event["app_id"] == "demo_app"
        assert event["run_id"] == "run_001"
        assert isinstance(event["details"], dict)
