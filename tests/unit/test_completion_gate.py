from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.completion_gate import (
    CaptureCounts,
    CompletionGate,
)
from ai_screenshot_platform.common.domain.run_status import RunStatus


def test_999_low_does_not_complete():
    decision = CompletionGate().evaluate(CaptureCounts(low=999))

    assert decision.valid_total == 999
    assert decision.has_main_bucket is True
    assert decision.next_status == RunStatus.RUNNING
    assert decision.should_stop_capture is False
    assert decision.reason == "below_target_min"


def test_1000_low_enters_capture_completed():
    decision = CompletionGate().evaluate(CaptureCounts(low=1000))

    assert decision.valid_total == 1000
    assert decision.has_main_bucket is True
    assert decision.next_status == RunStatus.CAPTURE_COMPLETED
    assert decision.should_stop_capture is False
    assert decision.reason == "target_min_reached"


def test_1000_high_enters_capture_completed():
    decision = CompletionGate().evaluate(CaptureCounts(high=1000))

    assert decision.valid_total == 1000
    assert decision.has_main_bucket is True
    assert decision.next_status == RunStatus.CAPTURE_COMPLETED
    assert decision.should_stop_capture is False
    assert decision.reason == "target_min_reached"


def test_1000_fixed_does_not_complete():
    decision = CompletionGate().evaluate(CaptureCounts(fixed=1000))

    assert decision.valid_total == 1000
    assert decision.has_main_bucket is False
    assert decision.next_status == RunStatus.RUNNING
    assert decision.should_stop_capture is True
    assert decision.reason == "fixed_cap_exceeded"


def test_fixed_over_10_is_invalid():
    decision = CompletionGate().evaluate(CaptureCounts(fixed=11, low=1000))

    assert decision.valid_total == 1011
    assert decision.next_status == RunStatus.RUNNING
    assert decision.should_stop_capture is True
    assert decision.reason == "fixed_cap_exceeded"


def test_low_and_high_zero_does_not_complete():
    decision = CompletionGate().evaluate(CaptureCounts(fixed=10))

    assert decision.valid_total == 10
    assert decision.has_main_bucket is False
    assert decision.next_status == RunStatus.RUNNING
    assert decision.should_stop_capture is False
    assert decision.reason == "main_bucket_required"


def test_valid_total_5000_with_main_bucket_stops_capture():
    decision = CompletionGate().evaluate(CaptureCounts(low=5000))

    assert decision.valid_total == 5000
    assert decision.has_main_bucket is True
    assert decision.next_status == RunStatus.CAPTURE_COMPLETED
    assert decision.should_stop_capture is True
    assert decision.reason == "target_max_reached"


def test_valid_total_over_5000_stops_capture_with_reason():
    decision = CompletionGate().evaluate(CaptureCounts(low=5001))

    assert decision.valid_total == 5001
    assert decision.has_main_bucket is True
    assert decision.next_status == RunStatus.RUNNING
    assert decision.should_stop_capture is True
    assert decision.reason == "target_max_exceeded"


def test_rejected_images_do_not_count_toward_valid_total():
    decision = CompletionGate().evaluate(CaptureCounts(low=999, rejected=5000))

    assert decision.valid_total == 999
    assert decision.next_status == RunStatus.RUNNING
    assert decision.reason == "below_target_min"


def test_bucket_values_are_limited_to_expected_buckets():
    assert {bucket.value for bucket in Bucket} == {"fixed", "low", "high", "rejected"}


def test_cleanup_completed_is_not_a_run_status():
    assert "cleanup_completed" not in {status.value for status in RunStatus}
    assert not hasattr(RunStatus, "CLEANUP_COMPLETED")


def test_legacy_run_statuses_are_not_run_statuses():
    status_values = {status.value for status in RunStatus}

    assert "created" not in status_values
    assert not hasattr(RunStatus, "CREATED")
    assert "capture_running" not in status_values
    assert not hasattr(RunStatus, "CAPTURE_RUNNING")


def test_completed_max_is_not_a_run_status():
    assert "completed_max" not in {status.value for status in RunStatus}
    assert not hasattr(RunStatus, "COMPLETED_MAX")


def test_local_deleted_is_a_run_status():
    assert RunStatus.LOCAL_DELETED.value == "local_deleted"
