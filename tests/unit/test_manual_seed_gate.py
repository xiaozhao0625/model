import json

import pytest

from ai_screenshot_platform.common.coverage.manual_seed_gate import ManualSeedError
from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_session(tmp_path, target_min=3):
    return LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="demo_app",
            run_id="run_001",
            target_min=target_min,
        )
    )


def test_running_request_manual_seed_enters_needs_manual_seed(tmp_path):
    session = make_session(tmp_path)
    session.start()

    record = session.request_manual_seed(
        reason="max_auto_retries_exhausted",
        retry_round=2,
        operator="tester",
        note="need seed",
    )

    assert session.status == RunStatus.NEEDS_MANUAL_SEED
    assert record.status == RunStatus.NEEDS_MANUAL_SEED.value
    assert record.event == "manual_seed_requested"


def test_request_manual_seed_writes_manual_seed_record_jsonl(tmp_path):
    session = make_session(tmp_path)
    session.start()

    session.request_manual_seed(
        reason="max_auto_retries_exhausted",
        retry_round=2,
        operator="tester",
        note="need seed",
    )
    records = read_jsonl(session.run_dir / "manual_seed_record.jsonl")

    assert records
    assert records[-1]["event"] == "manual_seed_requested"
    assert records[-1]["operator"] == "tester"


def test_request_manual_seed_writes_run_log_event(tmp_path):
    session = make_session(tmp_path)
    session.start()

    session.request_manual_seed(
        reason="max_auto_retries_exhausted",
        retry_round=2,
        operator="tester",
        note="need seed",
    )
    events = read_jsonl(session.run_log_path)

    assert "manual_seed_requested" in [event["event"] for event in events]


def test_resume_after_manual_seed_returns_to_running(tmp_path):
    session = make_session(tmp_path)
    session.start()
    session.request_manual_seed(
        reason="max_auto_retries_exhausted",
        retry_round=2,
        operator="tester",
        note="need seed",
    )

    record = session.resume_after_manual_seed(
        reason="manual_seed_added",
        retry_round=2,
        operator="tester",
        note="resume",
    )

    assert session.status == RunStatus.RUNNING
    assert record.status == RunStatus.RUNNING.value
    assert record.event == "manual_seed_completed"


def test_resume_after_manual_seed_writes_manual_seed_record_jsonl(tmp_path):
    session = make_session(tmp_path)
    session.start()
    session.request_manual_seed(
        reason="max_auto_retries_exhausted",
        retry_round=2,
        operator="tester",
        note="need seed",
    )
    session.resume_after_manual_seed(
        reason="manual_seed_added",
        retry_round=2,
        operator="tester",
        note="resume",
    )
    records = read_jsonl(session.run_dir / "manual_seed_record.jsonl")

    assert [record["event"] for record in records] == [
        "manual_seed_requested",
        "manual_seed_completed",
    ]


def test_resume_after_manual_seed_writes_run_log_event(tmp_path):
    session = make_session(tmp_path)
    session.start()
    session.request_manual_seed(
        reason="max_auto_retries_exhausted",
        retry_round=2,
        operator="tester",
        note="need seed",
    )
    session.resume_after_manual_seed(
        reason="manual_seed_added",
        retry_round=2,
        operator="tester",
        note="resume",
    )
    events = read_jsonl(session.run_log_path)

    assert "manual_seed_completed" in [event["event"] for event in events]


def test_capture_completed_request_manual_seed_fails(tmp_path):
    session = make_session(tmp_path, target_min=1)
    session.start()
    session.save_image(Bucket.LOW, b"low")
    session.evaluate_completion()

    with pytest.raises(ManualSeedError):
        session.request_manual_seed(
            reason="too_late",
            retry_round=2,
            operator="tester",
            note="invalid",
        )


def test_running_resume_after_manual_seed_fails(tmp_path):
    session = make_session(tmp_path)
    session.start()

    with pytest.raises(ManualSeedError):
        session.resume_after_manual_seed(
            reason="not_requested",
            retry_round=0,
            operator="tester",
            note="invalid",
        )


def test_completed_request_manual_seed_fails(tmp_path):
    session = make_session(tmp_path)
    session.status = RunStatus.COMPLETED

    with pytest.raises(ManualSeedError):
        session.request_manual_seed(
            reason="too_late",
            retry_round=2,
            operator="tester",
            note="invalid",
        )


def test_running_mark_failed_low_yield_enters_failed_low_yield(tmp_path):
    session = make_session(tmp_path)
    session.start()

    status = session.mark_failed_low_yield(
        reason="still_below_target",
        retry_round=2,
        operator="tester",
        note="stop",
    )

    assert status == RunStatus.FAILED_LOW_YIELD
    assert session.status == RunStatus.FAILED_LOW_YIELD


def test_failed_low_yield_does_not_enter_completed(tmp_path):
    session = make_session(tmp_path)
    session.start()
    session.mark_failed_low_yield(
        reason="still_below_target",
        retry_round=2,
        operator="tester",
        note="stop",
    )

    assert session.status != RunStatus.COMPLETED
