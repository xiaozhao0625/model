from dataclasses import dataclass

from ai_screenshot_platform.common.domain.run_status import RunStatus


class RunTransitionError(ValueError):
    pass


@dataclass(frozen=True)
class RunLifecycle:
    allowed_transitions: frozenset[tuple[RunStatus, RunStatus]] = frozenset(
        {
            (RunStatus.PENDING, RunStatus.LAUNCHING),
            (RunStatus.LAUNCHING, RunStatus.WAITING_MANUAL),
            (RunStatus.WAITING_MANUAL, RunStatus.PROFILING),
            (RunStatus.LAUNCHING, RunStatus.PROFILING),
            (RunStatus.PROFILING, RunStatus.RUNNING),
            (RunStatus.RUNNING, RunStatus.CAPTURE_COMPLETED),
            (RunStatus.CAPTURE_COMPLETED, RunStatus.UPLOAD_PENDING),
            (RunStatus.UPLOAD_PENDING, RunStatus.UPLOADED_CONFIRMED),
            (RunStatus.UPLOADED_CONFIRMED, RunStatus.LOCAL_DELETED),
            (RunStatus.LOCAL_DELETED, RunStatus.COMPLETED),
            (RunStatus.LAUNCHING, RunStatus.SKIPPED_RISK),
            (RunStatus.PROFILING, RunStatus.SKIPPED_RISK),
            (RunStatus.RUNNING, RunStatus.SKIPPED_RISK),
            (RunStatus.RUNNING, RunStatus.NEEDS_MANUAL_SEED),
            (RunStatus.NEEDS_MANUAL_SEED, RunStatus.RUNNING),
            (RunStatus.RUNNING, RunStatus.FAILED_LOW_YIELD),
        }
    )

    def can_transition(self, from_status: RunStatus, to_status: RunStatus) -> bool:
        return (from_status, to_status) in self.allowed_transitions

    def transition(self, from_status: RunStatus, to_status: RunStatus) -> RunStatus:
        if not self.can_transition(from_status, to_status):
            raise RunTransitionError(
                f"invalid run transition: {from_status.value} -> {to_status.value}"
            )
        return to_status
