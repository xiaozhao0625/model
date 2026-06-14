from __future__ import annotations

from ai_screenshot_platform.common.domain.run_lifecycle import RunLifecycle
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.models.entities import RunRecord
from ai_screenshot_platform.master.models.entities import RunStatusEvent
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

    def list_api(self) -> list[dict[str, int | str | None]]:
        return [self.to_api_record(record) for record in self.list()]

    def get(self, run_id: str) -> RunRecord:
        record = self.run_repo.get(run_id)
        if record is None:
            raise KeyError(f"run not found: {run_id}")
        return record

    def get_api(self, run_id: str) -> dict[str, int | str | None]:
        return self.to_api_record(self.get(run_id))

    def start_run(self, run_id: str) -> RunRecord:
        record = self.get(run_id)
        status = self.lifecycle.transition(record.status, RunStatus.LAUNCHING)
        status = self.lifecycle.transition(status, RunStatus.PROFILING)
        status = self.lifecycle.transition(status, RunStatus.RUNNING)
        return self.run_repo.update_status(run_id, status)

    def mark_failed_low_yield(
        self,
        run_id: str,
        operator_action: str = "mark_failed_low_yield",
    ) -> dict[str, int | str | None]:
        record = self.get(run_id)
        if record.status == RunStatus.SKIPPED_RISK:
            raise ValueError("skipped risk runs cannot be marked failed low yield")
        if record.status != RunStatus.FAILED_LOW_YIELD:
            self.run_repo.update_status(run_id, RunStatus.FAILED_LOW_YIELD)
            self.run_repo.record_status_event(
                run_id=run_id,
                previous_status=record.status,
                new_status=RunStatus.FAILED_LOW_YIELD,
                operator_action=operator_action,
            )
        return self.get_api(run_id)

    def status_events(self, run_id: str) -> list[RunStatusEvent]:
        self.get(run_id)
        return self.run_repo.status_events(run_id)

    def summary(self, run_id: str) -> dict[str, int | str | None]:
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
            "worker_id": self.worker_id_for(record),
            "assigned_worker_id": self.worker_id_for(record),
            "executed_by": self.worker_id_for(record),
        }

    def to_api_record(self, record: RunRecord) -> dict[str, int | str | None]:
        worker_id = self.worker_id_for(record)
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
            "worker_id": worker_id,
            "assigned_worker_id": worker_id,
            "executed_by": worker_id,
        }

    def worker_id_for(self, record: RunRecord) -> str | None:
        if record.worker_id:
            return record.worker_id
        return infer_worker_id_from_run_id(record.run_id)


def infer_worker_id_from_run_id(run_id: str) -> str | None:
    normalized = run_id.lower()
    if "_w1_" in normalized or normalized.startswith("p14_w1_") or "safe_window" in normalized:
        return "worker_pc_game_w1"
    if "_w2_" in normalized or normalized.startswith("p14_w2_") or "web_content" in normalized:
        return "worker_pc_app_web_w2"
    if "_w3_" in normalized or normalized.startswith("p14_w3_") or "android" in normalized:
        return "worker_android_w3"
    return None
