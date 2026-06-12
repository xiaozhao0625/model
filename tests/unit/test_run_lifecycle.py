import pytest

from ai_screenshot_platform.common.domain.run_lifecycle import (
    RunLifecycle,
    RunTransitionError,
)
from ai_screenshot_platform.common.domain.run_status import RunStatus


def test_main_path_transitions_are_valid():
    lifecycle = RunLifecycle()
    main_path = [
        RunStatus.PENDING,
        RunStatus.LAUNCHING,
        RunStatus.WAITING_MANUAL,
        RunStatus.PROFILING,
        RunStatus.RUNNING,
        RunStatus.CAPTURE_COMPLETED,
        RunStatus.UPLOAD_PENDING,
        RunStatus.UPLOADED_CONFIRMED,
        RunStatus.LOCAL_DELETED,
        RunStatus.COMPLETED,
    ]

    for from_status, to_status in zip(main_path, main_path[1:]):
        assert lifecycle.can_transition(from_status, to_status) is True
        assert lifecycle.transition(from_status, to_status) == to_status


def test_launching_to_profiling_skips_manual_gate():
    lifecycle = RunLifecycle()

    assert lifecycle.can_transition(RunStatus.LAUNCHING, RunStatus.PROFILING) is True


def test_running_to_needs_manual_seed_and_back_is_valid():
    lifecycle = RunLifecycle()

    assert lifecycle.transition(
        RunStatus.RUNNING,
        RunStatus.NEEDS_MANUAL_SEED,
    ) == RunStatus.NEEDS_MANUAL_SEED
    assert lifecycle.transition(
        RunStatus.NEEDS_MANUAL_SEED,
        RunStatus.RUNNING,
    ) == RunStatus.RUNNING


def test_running_to_failed_low_yield_is_valid():
    assert RunLifecycle().can_transition(
        RunStatus.RUNNING,
        RunStatus.FAILED_LOW_YIELD,
    )


def test_running_to_skipped_risk_is_valid():
    assert RunLifecycle().can_transition(
        RunStatus.RUNNING,
        RunStatus.SKIPPED_RISK,
    )


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (RunStatus.CAPTURE_COMPLETED, RunStatus.COMPLETED),
        (RunStatus.UPLOAD_PENDING, RunStatus.COMPLETED),
        (RunStatus.PENDING, RunStatus.COMPLETED),
        (RunStatus.UPLOADED_CONFIRMED, RunStatus.COMPLETED),
        (RunStatus.FAILED_LOW_YIELD, RunStatus.RUNNING),
        (RunStatus.SKIPPED_RISK, RunStatus.RUNNING),
        (RunStatus.COMPLETED, RunStatus.RUNNING),
    ],
)
def test_invalid_transitions_raise(from_status, to_status):
    lifecycle = RunLifecycle()

    assert lifecycle.can_transition(from_status, to_status) is False
    with pytest.raises(RunTransitionError):
        lifecycle.transition(from_status, to_status)


def test_run_status_contains_local_deleted():
    assert RunStatus.LOCAL_DELETED.value == "local_deleted"


def test_run_status_does_not_contain_cleanup_completed():
    assert "cleanup_completed" not in {status.value for status in RunStatus}
    assert not hasattr(RunStatus, "CLEANUP_COMPLETED")


def test_transition_error_message_contains_from_and_to_status():
    lifecycle = RunLifecycle()

    with pytest.raises(RunTransitionError) as exc_info:
        lifecycle.transition(RunStatus.PENDING, RunStatus.COMPLETED)

    message = str(exc_info.value)
    assert "pending" in message
    assert "completed" in message
