from ai_screenshot_platform.common.coverage.retry_policy import (
    RetryAction,
    RetryPolicy,
    RetryReason,
    RetryState,
)
from ai_screenshot_platform.common.domain.completion_gate import CaptureCounts
from ai_screenshot_platform.common.domain.run_status import RunStatus


def test_below_target_with_retry_available_continues_capture():
    decision = RetryPolicy.evaluate(
        CaptureCounts(low=999),
        RetryState(retry_round=0),
    )

    assert decision.action == RetryAction.CONTINUE_CAPTURE
    assert decision.reason == RetryReason.AUTO_RETRY_AVAILABLE
    assert decision.recommended_status == RunStatus.RUNNING
    assert decision.should_retry is True
    assert decision.next_retry_round == 1


def test_below_target_with_retries_exhausted_requests_manual_seed():
    decision = RetryPolicy.evaluate(
        CaptureCounts(low=999),
        RetryState(retry_round=2, max_auto_retries=2),
    )

    assert decision.action == RetryAction.REQUEST_MANUAL_SEED
    assert decision.reason == RetryReason.MAX_AUTO_RETRIES_EXHAUSTED
    assert decision.recommended_status == RunStatus.NEEDS_MANUAL_SEED
    assert decision.should_request_manual_seed is True


def test_1000_low_is_already_sufficient():
    decision = RetryPolicy.evaluate(
        CaptureCounts(low=1000),
        RetryState(retry_round=0),
    )

    assert decision.action == RetryAction.NONE
    assert decision.reason == RetryReason.ALREADY_SUFFICIENT
    assert decision.recommended_status == RunStatus.CAPTURE_COMPLETED
    assert decision.should_retry is False


def test_1000_high_is_capture_completed():
    decision = RetryPolicy.evaluate(
        CaptureCounts(high=1000),
        RetryState(retry_round=0),
    )

    assert decision.recommended_status == RunStatus.CAPTURE_COMPLETED
    assert decision.action == RetryAction.NONE


def test_fixed_only_missing_main_bucket_switches_strategy_before_retry_exhausted():
    decision = RetryPolicy.evaluate(
        CaptureCounts(fixed=1000),
        RetryState(retry_round=0),
        fixed_cap=1000,
    )

    assert decision.action == RetryAction.SWITCH_STRATEGY
    assert decision.reason == RetryReason.MISSING_MAIN_BUCKET
    assert decision.recommended_status == RunStatus.RUNNING
    assert decision.should_retry is True


def test_fixed_only_missing_main_bucket_requests_manual_seed_after_retries_exhausted():
    decision = RetryPolicy.evaluate(
        CaptureCounts(fixed=1000),
        RetryState(retry_round=2, max_auto_retries=2),
        fixed_cap=1000,
    )

    assert decision.action == RetryAction.REQUEST_MANUAL_SEED
    assert decision.reason == RetryReason.MAX_AUTO_RETRIES_EXHAUSTED
    assert decision.recommended_status == RunStatus.NEEDS_MANUAL_SEED


def test_rejected_does_not_count_toward_valid_total():
    decision = RetryPolicy.evaluate(
        CaptureCounts(low=999, rejected=1000),
        RetryState(retry_round=0),
    )

    assert decision.coverage_decision.valid_total == 999
    assert decision.action == RetryAction.CONTINUE_CAPTURE


def test_fixed_over_cap_fails_low_yield():
    decision = RetryPolicy.evaluate(
        CaptureCounts(fixed=11, low=999),
        RetryState(retry_round=0),
    )

    assert decision.action == RetryAction.FAIL_LOW_YIELD
    assert decision.reason == RetryReason.FIXED_CAP_EXCEEDED
    assert decision.recommended_status == RunStatus.FAILED_LOW_YIELD
    assert decision.should_fail is True


def test_target_max_reached_is_capture_completed_without_retry():
    decision = RetryPolicy.evaluate(
        CaptureCounts(low=5000),
        RetryState(retry_round=0),
    )

    assert decision.action == RetryAction.NONE
    assert decision.reason == RetryReason.TARGET_MAX_REACHED
    assert decision.recommended_status == RunStatus.CAPTURE_COMPLETED
    assert decision.should_retry is False


def test_target_max_exceeded_fails_low_yield():
    decision = RetryPolicy.evaluate(
        CaptureCounts(low=5001),
        RetryState(retry_round=0),
    )

    assert decision.action == RetryAction.FAIL_LOW_YIELD
    assert decision.reason == RetryReason.TARGET_MAX_EXCEEDED
    assert decision.recommended_status == RunStatus.FAILED_LOW_YIELD
    assert decision.should_fail is True


def test_retry_policy_does_not_add_forbidden_statuses():
    statuses = {status.value for status in RunStatus}

    assert "cleanup_completed" not in statuses
    assert "completed_max" not in statuses
    assert "retrying" not in statuses
