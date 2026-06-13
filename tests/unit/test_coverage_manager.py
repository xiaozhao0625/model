from ai_screenshot_platform.common.coverage.coverage_manager import (
    CoverageManager,
    CoverageReason,
)
from ai_screenshot_platform.common.domain.completion_gate import CaptureCounts
from ai_screenshot_platform.common.domain.run_status import RunStatus


def test_999_low_is_below_target_min():
    decision = CoverageManager.evaluate(CaptureCounts(low=999))

    assert decision.reason == CoverageReason.BELOW_TARGET_MIN
    assert decision.is_sufficient is False
    assert decision.needs_more_capture is True
    assert decision.recommended_status == RunStatus.RUNNING


def test_1000_low_is_sufficient_and_recommends_capture_completed():
    decision = CoverageManager.evaluate(CaptureCounts(low=1000))

    assert decision.reason == CoverageReason.SUFFICIENT
    assert decision.is_sufficient is True
    assert decision.recommended_status == RunStatus.CAPTURE_COMPLETED


def test_1000_high_is_sufficient():
    decision = CoverageManager.evaluate(CaptureCounts(high=1000))

    assert decision.reason == CoverageReason.SUFFICIENT
    assert decision.is_sufficient is True


def test_fixed_only_does_not_satisfy_when_main_bucket_is_missing():
    decision = CoverageManager.evaluate(
        CaptureCounts(fixed=1000),
        fixed_cap=1000,
    )

    assert decision.reason == CoverageReason.MISSING_MAIN_BUCKET
    assert decision.missing_main_bucket is True
    assert decision.is_sufficient is False


def test_low_and_high_zero_marks_missing_main_bucket():
    decision = CoverageManager.evaluate(CaptureCounts(fixed=3, rejected=500))

    assert decision.missing_main_bucket is True
    assert decision.reason == CoverageReason.MISSING_MAIN_BUCKET


def test_rejected_does_not_count_toward_valid_total():
    decision = CoverageManager.evaluate(CaptureCounts(low=999, rejected=1000))

    assert decision.valid_total == 999
    assert decision.reason == CoverageReason.BELOW_TARGET_MIN


def test_fixed_over_cap_returns_fixed_cap_exceeded():
    decision = CoverageManager.evaluate(CaptureCounts(fixed=11, low=999))

    assert decision.reason == CoverageReason.FIXED_CAP_EXCEEDED
    assert decision.should_stop_capture is True
    assert decision.recommended_status == RunStatus.RUNNING


def test_target_max_reached_stops_capture():
    decision = CoverageManager.evaluate(CaptureCounts(low=5000))

    assert decision.reason == CoverageReason.TARGET_MAX_REACHED
    assert decision.should_stop_capture is True
    assert decision.is_sufficient is True


def test_target_max_exceeded_stops_capture_with_reason():
    decision = CoverageManager.evaluate(CaptureCounts(low=5001))

    assert decision.reason == CoverageReason.TARGET_MAX_EXCEEDED
    assert decision.should_stop_capture is True
    assert decision.is_sufficient is False


def test_coverage_manager_does_not_add_forbidden_statuses():
    statuses = {status.value for status in RunStatus}

    assert "cleanup_completed" not in statuses
    assert "completed_max" not in statuses
