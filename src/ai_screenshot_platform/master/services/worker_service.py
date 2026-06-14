from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ai_screenshot_platform.common.domain.run_lifecycle import RunLifecycle
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.worker.contracts import WorkerTask
from ai_screenshot_platform.master.models.entities import AppRecord
from ai_screenshot_platform.master.models.entities import WorkerRecord
from ai_screenshot_platform.master.repositories.app_repo import AppRepo
from ai_screenshot_platform.master.repositories.run_repo import RunRepo
from ai_screenshot_platform.master.repositories.worker_repo import WorkerRepo


class WorkerService:
    forbidden_report_statuses = {
        RunStatus.UPLOAD_PENDING,
        RunStatus.UPLOADED_CONFIRMED,
        RunStatus.LOCAL_DELETED,
        RunStatus.COMPLETED,
    }

    def __init__(
        self,
        worker_repo: WorkerRepo,
        run_repo: RunRepo | None = None,
        app_repo: AppRepo | None = None,
        data_root: str | Path = "runs/worker_agent",
        lifecycle: RunLifecycle | None = None,
    ) -> None:
        self.worker_repo = worker_repo
        self.run_repo = run_repo
        self.app_repo = app_repo
        self.data_root = Path(data_root)
        self.lifecycle = lifecycle or RunLifecycle()

    def register(
        self,
        worker_id: str,
        type: str,
        capabilities: list[str],
        machine_name: str | None = None,
    ) -> WorkerRecord:
        return self.worker_repo.upsert(
            WorkerRecord(
                worker_id=worker_id,
                type=type,
                machine_name=machine_name,
                capabilities=capabilities,
                state="idle",
                heartbeat=datetime.now(timezone.utc).isoformat(),
                current_run_id=None,
            )
        )

    def list(self) -> list[WorkerRecord]:
        return self.worker_repo.list()

    def heartbeat(self, worker_id: str) -> WorkerRecord:
        existing = self.worker_repo.get(worker_id)
        if existing is None:
            raise KeyError(f"worker not found: {worker_id}")
        return self.worker_repo.upsert(
            WorkerRecord(
                worker_id=existing.worker_id,
                type=existing.type,
                machine_name=existing.machine_name,
                capabilities=existing.capabilities,
                state=existing.state,
                heartbeat=datetime.now(timezone.utc).isoformat(),
                current_run_id=existing.current_run_id,
            )
        )

    def assign(self) -> WorkerRecord | None:
        for worker in self.worker_repo.list():
            if worker.state == "idle":
                return worker
        return None

    def claim(self, worker_id: str) -> dict[str, object]:
        if self.run_repo is None or self.app_repo is None:
            raise ValueError("worker claim requires run and app repositories")
        worker = self.worker_repo.get(worker_id)
        if worker is None:
            raise KeyError(f"worker not found: {worker_id}")
        if worker.current_run_id:
            return {"status": "busy", "task": None}

        for run in self.run_repo.list():
            if run.status != RunStatus.PENDING:
                continue
            app = self.app_repo.get(run.app_id)
            if app is None or not self._can_accept(worker, app):
                continue
            status = self.lifecycle.transition(run.status, RunStatus.LAUNCHING)
            status = self.lifecycle.transition(status, RunStatus.PROFILING)
            status = self.lifecycle.transition(status, RunStatus.RUNNING)
            self.run_repo.update_status(run.run_id, status, worker_id=worker.worker_id)
            self.worker_repo.upsert(
                WorkerRecord(
                    worker_id=worker.worker_id,
                    type=worker.type,
                    machine_name=worker.machine_name,
                    capabilities=worker.capabilities,
                    state="running",
                    heartbeat=datetime.now(timezone.utc).isoformat(),
                    current_run_id=run.run_id,
                )
            )
            return {
                "status": "claimed",
                "task": WorkerTask(
                    app_id=run.app_id,
                    run_id=run.run_id,
                    app_type=app.type,
                    platform=app.platform,
                    target_min=run.target_min,
                    target_max=run.target_max,
                    bucket=self._default_bucket(app),
                    root_dir=self.data_root / "assigned_runs",
                ),
            }

        return {"status": "no_task", "task": None}

    def report(self, worker_id: str, run_id: str, result) -> dict[str, object]:
        if self.run_repo is None:
            raise ValueError("worker report requires run repository")
        worker = self.worker_repo.get(worker_id)
        if worker is None:
            raise KeyError(f"worker not found: {worker_id}")
        run = self.run_repo.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        if worker.current_run_id not in {None, run_id}:
            raise ValueError(
                f"worker {worker_id} is assigned to {worker.current_run_id}, not {run_id}"
            )

        status = RunStatus(result.status)
        if status in self.forbidden_report_statuses:
            raise ValueError(f"worker report cannot set run status to {status.value}")

        updated_run = self.run_repo.update_from_worker_result(
            run_id=run_id,
            status=status,
            valid_total=result.valid_total,
            fixed_count=result.fixed_count,
            low_count=result.low_count,
            high_count=result.high_count,
            rejected_count=result.rejected_count,
            worker_id=worker_id,
        )
        updated_worker = self.worker_repo.upsert(
            WorkerRecord(
                worker_id=worker.worker_id,
                type=worker.type,
                machine_name=worker.machine_name,
                capabilities=worker.capabilities,
                state="idle",
                heartbeat=datetime.now(timezone.utc).isoformat(),
                current_run_id=None,
            )
        )
        return {"run": updated_run, "worker": updated_worker}

    def _can_accept(self, worker: WorkerRecord, app: AppRecord) -> bool:
        capabilities = set(worker.capabilities)
        if worker.type == "mock":
            return True
        if app.type == "pc_game":
            return "capture_high" in capabilities
        return "capture_low" in capabilities

    def _default_bucket(self, app: AppRecord) -> str:
        return "high" if app.type == "pc_game" else "low"
