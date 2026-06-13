from __future__ import annotations

from datetime import datetime, timezone

from ai_screenshot_platform.master.models.entities import WorkerRecord
from ai_screenshot_platform.master.repositories.worker_repo import WorkerRepo


class WorkerService:
    def __init__(self, worker_repo: WorkerRepo) -> None:
        self.worker_repo = worker_repo

    def register(
        self,
        worker_id: str,
        type: str,
        capabilities: list[str],
    ) -> WorkerRecord:
        return self.worker_repo.upsert(
            WorkerRecord(
                worker_id=worker_id,
                type=type,
                capabilities=capabilities,
                state="idle",
                heartbeat=datetime.now(timezone.utc).isoformat(),
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
                capabilities=existing.capabilities,
                state=existing.state,
                heartbeat=datetime.now(timezone.utc).isoformat(),
            )
        )

    def assign(self) -> WorkerRecord | None:
        for worker in self.worker_repo.list():
            if worker.state == "idle":
                return worker
        return None
