from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_screenshot_platform.common.coverage.coverage_manager import (
    CoverageDecision,
    CoverageManager,
    CoverageReason,
)
from ai_screenshot_platform.common.domain.completion_gate import CaptureCounts
from ai_screenshot_platform.common.domain.run_status import RunStatus


class RetryAction(StrEnum):
    NONE = "none"
    CONTINUE_CAPTURE = "continue_capture"
    SWITCH_STRATEGY = "switch_strategy"
    REQUEST_MANUAL_SEED = "request_manual_seed"
    FAIL_LOW_YIELD = "fail_low_yield"


class RetryReason(StrEnum):
    ALREADY_SUFFICIENT = "already_sufficient"
    BELOW_TARGET_MIN = "below_target_min"
    MISSING_MAIN_BUCKET = "missing_main_bucket"
    AUTO_RETRY_AVAILABLE = "auto_retry_available"
    MAX_AUTO_RETRIES_EXHAUSTED = "max_auto_retries_exhausted"
    TARGET_MAX_REACHED = "target_max_reached"
    TARGET_MAX_EXCEEDED = "target_max_exceeded"
    FIXED_CAP_EXCEEDED = "fixed_cap_exceeded"


@dataclass(frozen=True)
class RetryState:
    retry_round: int
    max_auto_retries: int = 2
    last_strategy: str | None = None

    def __post_init__(self) -> None:
        if self.retry_round < 0:
            raise ValueError("retry_round must be non-negative")
        if self.max_auto_retries < 0:
            raise ValueError("max_auto_retries must be non-negative")


@dataclass(frozen=True)
class RetryDecision:
    action: RetryAction
    recommended_status: RunStatus
    current_retry_round: int
    next_retry_round: int
    should_retry: bool
    should_request_manual_seed: bool
    should_fail: bool
    reason: RetryReason
    coverage_decision: CoverageDecision


class RetryPolicy:
    @staticmethod
    def evaluate(
        counts: CaptureCounts,
        retry_state: RetryState,
        target_min: int = 1000,
        target_max: int = 5000,
        fixed_cap: int = 10,
    ) -> RetryDecision:
        coverage_decision = CoverageManager.evaluate(
            counts=counts,
            target_min=target_min,
            target_max=target_max,
            fixed_cap=fixed_cap,
        )

        if coverage_decision.reason == CoverageReason.FIXED_CAP_EXCEEDED:
            return RetryPolicy._decision(
                retry_state=retry_state,
                coverage_decision=coverage_decision,
                action=RetryAction.FAIL_LOW_YIELD,
                recommended_status=RunStatus.FAILED_LOW_YIELD,
                reason=RetryReason.FIXED_CAP_EXCEEDED,
                should_fail=True,
            )

        if coverage_decision.reason == CoverageReason.TARGET_MAX_EXCEEDED:
            return RetryPolicy._decision(
                retry_state=retry_state,
                coverage_decision=coverage_decision,
                action=RetryAction.FAIL_LOW_YIELD,
                recommended_status=RunStatus.FAILED_LOW_YIELD,
                reason=RetryReason.TARGET_MAX_EXCEEDED,
                should_fail=True,
            )

        if coverage_decision.reason == CoverageReason.TARGET_MAX_REACHED:
            return RetryPolicy._decision(
                retry_state=retry_state,
                coverage_decision=coverage_decision,
                action=RetryAction.NONE,
                recommended_status=RunStatus.CAPTURE_COMPLETED,
                reason=RetryReason.TARGET_MAX_REACHED,
            )

        if coverage_decision.is_sufficient:
            return RetryPolicy._decision(
                retry_state=retry_state,
                coverage_decision=coverage_decision,
                action=RetryAction.NONE,
                recommended_status=RunStatus.CAPTURE_COMPLETED,
                reason=RetryReason.ALREADY_SUFFICIENT,
            )

        if retry_state.retry_round >= retry_state.max_auto_retries:
            return RetryPolicy._decision(
                retry_state=retry_state,
                coverage_decision=coverage_decision,
                action=RetryAction.REQUEST_MANUAL_SEED,
                recommended_status=RunStatus.NEEDS_MANUAL_SEED,
                reason=RetryReason.MAX_AUTO_RETRIES_EXHAUSTED,
                should_request_manual_seed=True,
            )

        if coverage_decision.reason == CoverageReason.MISSING_MAIN_BUCKET:
            return RetryPolicy._decision(
                retry_state=retry_state,
                coverage_decision=coverage_decision,
                action=RetryAction.SWITCH_STRATEGY,
                recommended_status=RunStatus.RUNNING,
                reason=RetryReason.MISSING_MAIN_BUCKET,
                should_retry=True,
            )

        return RetryPolicy._decision(
            retry_state=retry_state,
            coverage_decision=coverage_decision,
            action=RetryAction.CONTINUE_CAPTURE,
            recommended_status=RunStatus.RUNNING,
            reason=RetryReason.AUTO_RETRY_AVAILABLE,
            should_retry=True,
        )

    @staticmethod
    def _decision(
        retry_state: RetryState,
        coverage_decision: CoverageDecision,
        action: RetryAction,
        recommended_status: RunStatus,
        reason: RetryReason,
        should_retry: bool = False,
        should_request_manual_seed: bool = False,
        should_fail: bool = False,
    ) -> RetryDecision:
        return RetryDecision(
            action=action,
            recommended_status=recommended_status,
            current_retry_round=retry_state.retry_round,
            next_retry_round=(
                retry_state.retry_round + 1 if should_retry else retry_state.retry_round
            ),
            should_retry=should_retry,
            should_request_manual_seed=should_request_manual_seed,
            should_fail=should_fail,
            reason=reason,
            coverage_decision=coverage_decision,
        )
