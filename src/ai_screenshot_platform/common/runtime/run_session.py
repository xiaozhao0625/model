from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.completion_gate import (
    CompletionDecision,
    CompletionGate,
)
from ai_screenshot_platform.common.coverage.manual_seed_gate import (
    ManualSeedError,
    ManualSeedGate,
    ManualSeedRecord,
)
from ai_screenshot_platform.common.domain.run_lifecycle import (
    RunLifecycle,
    RunTransitionError,
)
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.logging.run_logger import RunEventLogger
from ai_screenshot_platform.common.runtime.run_status_resolver import RunStatusResolver
from ai_screenshot_platform.common.storage.screenshot_store import (
    BucketedScreenshotStore,
    SaveImageResult,
)
from ai_screenshot_platform.common.upload.upload_confirmation import (
    UploadConfirmationManager,
)
from ai_screenshot_platform.common.upload.local_cleanup import LocalCleanupManager
from ai_screenshot_platform.common.upload.upload_manifest import UploadManifestGenerator


@dataclass(frozen=True)
class RunSessionConfig:
    root_dir: str | Path
    app_id: str
    run_id: str
    target_min: int = 1000
    target_max: int = 5000
    fixed_cap: int = 10


class LocalRunSession:
    def __init__(self, config: RunSessionConfig) -> None:
        self.config = config
        self.lifecycle = RunLifecycle()
        self.status = RunStatus.PENDING
        self.store = BucketedScreenshotStore.open_existing(
            root_dir=config.root_dir,
            app_id=config.app_id,
            run_id=config.run_id,
            fixed_cap=config.fixed_cap,
        )
        self.completion_gate = CompletionGate(
            target_min=config.target_min,
            target_max=config.target_max,
            fixed_cap=config.fixed_cap,
        )
        self.logger = RunEventLogger(
            run_dir=self.store.run_dir,
            app_id=config.app_id,
            run_id=config.run_id,
        )
        self.upload_manifest_generator = UploadManifestGenerator()
        self.upload_confirmation_manager = UploadConfirmationManager()
        self.local_cleanup_manager = LocalCleanupManager()
        self.status_resolver = RunStatusResolver(self.completion_gate)
        self.manual_seed_gate = ManualSeedGate(
            run_dir=self.run_dir,
            app_id=config.app_id,
            run_id=config.run_id,
            lifecycle=self.lifecycle,
        )

    @property
    def run_dir(self) -> Path:
        return self.store.run_dir

    @property
    def run_log_path(self) -> Path:
        return self.logger.log_path

    @property
    def upload_manifest_path(self) -> Path:
        return self.run_dir / "upload_manifest.json"

    @property
    def upload_record_path(self) -> Path:
        return self.run_dir / "upload_record.json"

    @property
    def cleanup_record_path(self) -> Path:
        return self.run_dir / "cleanup_record.json"

    @property
    def manual_seed_record_path(self) -> Path:
        return self.run_dir / "manual_seed_record.jsonl"

    def start(self) -> RunStatus:
        self._transition_to(RunStatus.LAUNCHING)
        self._transition_to(RunStatus.PROFILING)
        self._transition_to(RunStatus.RUNNING)
        self.logger.log("session_started", self.status)
        return self.status

    def save_image(
        self,
        bucket: Bucket | str,
        image_bytes: bytes,
        reject_reason: str | None = None,
    ) -> SaveImageResult:
        result = self.store.save_image(
            bucket=bucket,
            image_bytes=image_bytes,
            reject_reason=reject_reason,
        )
        if result.reason == "duplicate_content_hash":
            self.logger.log(
                "duplicate_rejected",
                self.status,
                {
                    "reason": result.reason,
                    "duplicate_of": result.duplicate_of,
                },
            )
            return result

        if result.saved and result.meta is not None:
            self.logger.log(
                "image_saved",
                self.status,
                {
                    "image_id": result.meta["image_id"],
                    "bucket": result.meta["bucket"],
                    "path": result.meta["path"],
                    "valid": result.meta["valid"],
                    "reason": result.reason,
                },
            )
            return result

        self.logger.log(
            "image_rejected",
            self.status,
            {
                "reason": result.reason,
                "duplicate_of": result.duplicate_of,
            },
        )
        return result

    def evaluate_completion(self) -> CompletionDecision:
        decision = self.completion_gate.evaluate(self.store.capture_counts())
        if (
            self.status == RunStatus.RUNNING
            and decision.next_status == RunStatus.CAPTURE_COMPLETED
        ):
            self._transition_to(RunStatus.CAPTURE_COMPLETED)
            self.logger.log(
                "capture_completed",
                self.status,
                {
                    "valid_total": decision.valid_total,
                    "reason": decision.reason,
                    "should_stop_capture": decision.should_stop_capture,
                },
            )
        return decision

    def generate_summary(self) -> dict[str, int | str]:
        return self.store.generate_summary()

    def generate_upload_manifest(
        self,
        expected_upload_folder: str,
    ) -> dict[str, int | str | bool]:
        manifest = self.upload_manifest_generator.generate(
            run_dir=self.run_dir,
            expected_upload_folder=expected_upload_folder,
            current_status=self.status,
        )
        self._transition_to(RunStatus.UPLOAD_PENDING)
        return manifest

    def confirm_uploaded(
        self,
        confirmed_by: str,
        actual_upload_folder: str | None = None,
    ) -> dict[str, int | str | bool]:
        record = self.upload_confirmation_manager.confirm(
            run_dir=self.run_dir,
            current_status=self.status,
            confirmed_by=confirmed_by,
            actual_upload_folder=actual_upload_folder,
        )
        self._transition_to(RunStatus.UPLOADED_CONFIRMED)
        self.logger.log(
            "upload_confirmed",
            self.status,
            {
                "confirmed_by": confirmed_by,
                "actual_upload_folder": record["actual_upload_folder"],
                "expected_upload_folder": record["expected_upload_folder"],
                "delete_allowed": record["delete_allowed"],
            },
        )
        return record

    def cleanup_local_files(self) -> dict[str, int | str | list[str]]:
        previous_status = self.status
        record = self.local_cleanup_manager.cleanup(
            run_dir=self.run_dir,
            current_status=self.status,
        )
        if previous_status == RunStatus.UPLOADED_CONFIRMED:
            self._transition_to(RunStatus.LOCAL_DELETED)
        self.logger.log(
            "local_deleted",
            self.status,
            {
                "deleted_dirs": record["deleted_dirs"],
                "deleted_file_count": record["deleted_file_count"],
                "deleted_total_bytes": record["deleted_total_bytes"],
            },
        )
        return record

    def finalize_completed(self) -> RunStatus:
        self._transition_to(RunStatus.COMPLETED)
        self.logger.log("completed", self.status)
        return self.status

    def request_manual_seed(
        self,
        reason: str,
        retry_round: int,
        operator: str,
        note: str = "",
    ) -> ManualSeedRecord:
        record = self.manual_seed_gate.request_manual_seed(
            current_status=self.status,
            reason=reason,
            retry_round=retry_round,
            operator=operator,
            note=note,
        )
        self.status = RunStatus(record.status)
        self.logger.log(
            "manual_seed_requested",
            self.status,
            {
                "reason": reason,
                "retry_round": retry_round,
                "operator": operator,
                "note": note,
            },
        )
        return record

    def resume_after_manual_seed(
        self,
        reason: str,
        retry_round: int,
        operator: str,
        note: str = "",
    ) -> ManualSeedRecord:
        record = self.manual_seed_gate.resume_after_manual_seed(
            current_status=self.status,
            reason=reason,
            retry_round=retry_round,
            operator=operator,
            note=note,
        )
        self.status = RunStatus(record.status)
        self.logger.log(
            "manual_seed_completed",
            self.status,
            {
                "reason": reason,
                "retry_round": retry_round,
                "operator": operator,
                "note": note,
            },
        )
        return record

    def mark_failed_low_yield(
        self,
        reason: str,
        retry_round: int,
        operator: str,
        note: str = "",
    ) -> RunStatus:
        try:
            self._transition_to(RunStatus.FAILED_LOW_YIELD)
        except RunTransitionError as error:
            raise ManualSeedError(str(error)) from error
        self.logger.log(
            "failed_low_yield",
            self.status,
            {
                "reason": reason,
                "retry_round": retry_round,
                "operator": operator,
                "note": note,
            },
        )
        return self.status

    def restore_status(self) -> RunStatus:
        self.status = self.status_resolver.resolve(self.run_dir)
        return self.status

    def _transition_to(self, next_status: RunStatus) -> None:
        self.status = self.lifecycle.transition(self.status, next_status)
