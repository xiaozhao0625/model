from dataclasses import dataclass

from ai_screenshot_platform.common.domain.run_status import RunStatus


@dataclass(frozen=True)
class CaptureCounts:
    fixed: int = 0
    low: int = 0
    high: int = 0
    rejected: int = 0

    def __post_init__(self) -> None:
        for field_name in ("fixed", "low", "high", "rejected"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")

    @property
    def valid_total(self) -> int:
        return self.fixed + self.low + self.high

    @property
    def has_main_bucket(self) -> bool:
        return self.low > 0 or self.high > 0


@dataclass(frozen=True)
class CompletionDecision:
    next_status: RunStatus
    valid_total: int
    has_main_bucket: bool
    should_stop_capture: bool
    reason: str


class CompletionGate:
    def __init__(
        self,
        target_min: int = 1000,
        target_max: int = 5000,
        fixed_cap: int = 10,
    ) -> None:
        if target_min < 1:
            raise ValueError("target_min must be positive")
        if target_max < target_min:
            raise ValueError("target_max must be greater than or equal to target_min")
        if fixed_cap < 0:
            raise ValueError("fixed_cap must be non-negative")

        self.target_min = target_min
        self.target_max = target_max
        self.fixed_cap = fixed_cap

    def evaluate(self, counts: CaptureCounts) -> CompletionDecision:
        valid_total = counts.valid_total
        has_main_bucket = counts.has_main_bucket

        if counts.fixed > self.fixed_cap:
            return CompletionDecision(
                next_status=RunStatus.RUNNING,
                valid_total=valid_total,
                has_main_bucket=has_main_bucket,
                should_stop_capture=True,
                reason="fixed_cap_exceeded",
            )

        if valid_total > self.target_max:
            return CompletionDecision(
                next_status=RunStatus.RUNNING,
                valid_total=valid_total,
                has_main_bucket=has_main_bucket,
                should_stop_capture=True,
                reason="target_max_exceeded",
            )

        if not has_main_bucket:
            return CompletionDecision(
                next_status=RunStatus.RUNNING,
                valid_total=valid_total,
                has_main_bucket=False,
                should_stop_capture=False,
                reason="main_bucket_required",
            )

        if valid_total == self.target_max:
            return CompletionDecision(
                next_status=RunStatus.CAPTURE_COMPLETED,
                valid_total=valid_total,
                has_main_bucket=True,
                should_stop_capture=True,
                reason="target_max_reached",
            )

        if valid_total >= self.target_min:
            return CompletionDecision(
                next_status=RunStatus.CAPTURE_COMPLETED,
                valid_total=valid_total,
                has_main_bucket=True,
                should_stop_capture=False,
                reason="target_min_reached",
            )

        return CompletionDecision(
            next_status=RunStatus.RUNNING,
            valid_total=valid_total,
            has_main_bucket=True,
            should_stop_capture=False,
            reason="below_target_min",
        )
