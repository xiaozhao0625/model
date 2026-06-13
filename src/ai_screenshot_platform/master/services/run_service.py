from __future__ import annotations

from ai_screenshot_platform.common.domain.run_lifecycle import RunLifecycle
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.models.entities import RunRecord
from ai_screenshot_platform.master.repositories.run_repo import RunRepo


class RunService:
    def __init__(
        self,
        run_repo: RunRepo,
        lifecycle: RunLifecycle | None = None,
    ) -> None:
        self.run_repo = run_repo
        self.lifecycle = lifecycle or RunLifecycle()

    def create_run(
        self,
        run_id: str,
        app_id: str,
        target_min: int = 1000,
        target_max: int = 5000,
    ) -> RunRecord:
        return self.run_repo.create(
            RunRecord(
                run_id=run_id,
                app_id=app_id,
                status=RunStatus.PENDING,
                target_min=target_min,
                target_max=target_max,
            )
        )

    def list(self) -> list[RunRecord]:
        return self.run_repo.list()

    def get(self, run_id: str) -> RunRecord:
        record = self.run_repo.get(run_id)
        if record is None:
            raise KeyError(f"run not found: {run_id}")
        return record

    def start_run(self, run_id: str) -> RunRecord:
        record = self.get(run_id)
        status = self.lifecycle.transition(record.status, RunStatus.LAUNCHING)
        status = self.lifecycle.transition(status, RunStatus.PROFILING)
        status = self.lifecycle.transition(status, RunStatus.RUNNING)
        return self.run_repo.update_status(run_id, status)

    def summary(self, run_id: str) -> dict[str, int | str]:
        record = self.get(run_id)
        return {
            "run_id": record.run_id,
            "app_id": record.app_id,
            "status": record.status.value,
            "target_min": record.target_min,
            "target_max": record.target_max,
            "valid_total": record.valid_total,
            "fixed_count": record.fixed_count,
            "low_count": record.low_count,
            "high_count": record.high_count,
            "rejected_count": record.rejected_count,
            "retry_round": record.retry_round,
        }
