from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_screenshot_platform.common.domain.completion_gate import (
    CaptureCounts,
    CompletionGate,
)
from ai_screenshot_platform.common.domain.run_status import RunStatus


class CoverageReason(StrEnum):
    SUFFICIENT = "sufficient"
    BELOW_TARGET_MIN = "below_target_min"
    MISSING_MAIN_BUCKET = "missing_main_bucket"
    FIXED_CAP_EXCEEDED = "fixed_cap_exceeded"
    TARGET_MAX_REACHED = "target_max_reached"
    TARGET_MAX_EXCEEDED = "target_max_exceeded"


@dataclass(frozen=True)
class CoverageDecision:
    valid_total: int
    has_main_bucket: bool
    is_sufficient: bool
    needs_more_capture: bool
    missing_main_bucket: bool
    should_stop_capture: bool
    recommended_status: RunStatus
    reason: CoverageReason


class CoverageManager:
    @staticmethod
    def evaluate(
        counts: CaptureCounts,
        target_min: int = 1000,
        target_max: int = 5000,
        fixed_cap: int = 10,
    ) -> CoverageDecision:
        completion_decision = CompletionGate(
            target_min=target_min,
            target_max=target_max,
            fixed_cap=fixed_cap,
        ).evaluate(counts)

        reason = CoverageManager._map_reason(completion_decision.reason)
        is_sufficient = (
            completion_decision.next_status == RunStatus.CAPTURE_COMPLETED
            and reason in {CoverageReason.SUFFICIENT, CoverageReason.TARGET_MAX_REACHED}
        )
        missing_main_bucket = not completion_decision.has_main_bucket
        needs_more_capture = (
            not is_sufficient
            and not completion_decision.should_stop_capture
            and not missing_main_bucket
        )

        return CoverageDecision(
            valid_total=completion_decision.valid_total,
            has_main_bucket=completion_decision.has_main_bucket,
            is_sufficient=is_sufficient,
            needs_more_capture=needs_more_capture,
            missing_main_bucket=missing_main_bucket,
            should_stop_capture=completion_decision.should_stop_capture,
            recommended_status=(
                RunStatus.CAPTURE_COMPLETED if is_sufficient else RunStatus.RUNNING
            ),
            reason=reason,
        )

    @staticmethod
    def _map_reason(reason: str) -> CoverageReason:
        if reason == "target_min_reached":
            return CoverageReason.SUFFICIENT
        if reason == "main_bucket_required":
            return CoverageReason.MISSING_MAIN_BUCKET
        return CoverageReason(reason)
