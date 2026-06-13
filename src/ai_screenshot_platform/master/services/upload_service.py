from __future__ import annotations

from ai_screenshot_platform.common.domain.run_lifecycle import RunLifecycle
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.models.entities import UploadRecord
from ai_screenshot_platform.master.repositories.run_repo import RunRepo
from ai_screenshot_platform.master.repositories.upload_repo import UploadRepo


class UploadService:
    def __init__(
        self,
        run_repo: RunRepo,
        upload_repo: UploadRepo,
        lifecycle: RunLifecycle | None = None,
    ) -> None:
        self.run_repo = run_repo
        self.upload_repo = upload_repo
        self.lifecycle = lifecycle or RunLifecycle()

    def manifest(self, run_id: str) -> UploadRecord:
        record = self._get_run(run_id)
        status = record.status
        if status == RunStatus.RUNNING:
            status = self.lifecycle.transition(status, RunStatus.CAPTURE_COMPLETED)
        status = self.lifecycle.transition(status, RunStatus.UPLOAD_PENDING)
        self.run_repo.update_status(run_id, status)
        return self.upload_repo.upsert(
            UploadRecord(
                upload_id=f"{run_id}:manifest",
                run_id=run_id,
                status=status,
            )
        )

    def confirm(self, run_id: str) -> UploadRecord:
        status = self.lifecycle.transition(
            self._get_run(run_id).status,
            RunStatus.UPLOADED_CONFIRMED,
        )
        self.run_repo.update_status(run_id, status)
        return self.upload_repo.upsert(
            UploadRecord(upload_id=f"{run_id}:confirm", run_id=run_id, status=status)
        )

    def cleanup(self, run_id: str) -> UploadRecord:
        status = self.lifecycle.transition(
            self._get_run(run_id).status,
            RunStatus.LOCAL_DELETED,
        )
        self.run_repo.update_status(run_id, status)
        return self.upload_repo.upsert(
            UploadRecord(upload_id=f"{run_id}:cleanup", run_id=run_id, status=status)
        )

    def finalize(self, run_id: str) -> UploadRecord:
        status = self.lifecycle.transition(
            self._get_run(run_id).status,
            RunStatus.COMPLETED,
        )
        self.run_repo.update_status(run_id, status)
        return self.upload_repo.upsert(
            UploadRecord(upload_id=f"{run_id}:finalize", run_id=run_id, status=status)
        )

    def _get_run(self, run_id: str):
        record = self.run_repo.get(run_id)
        if record is None:
            raise KeyError(f"run not found: {run_id}")
        return record
