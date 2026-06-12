from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.completion_gate import (
    CompletionDecision,
    CompletionGate,
)
from ai_screenshot_platform.common.domain.run_lifecycle import RunLifecycle
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.logging.run_logger import RunEventLogger
from ai_screenshot_platform.common.storage.screenshot_store import (
    BucketedScreenshotStore,
    SaveImageResult,
)


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

    @property
    def run_dir(self) -> Path:
        return self.store.run_dir

    @property
    def run_log_path(self) -> Path:
        return self.logger.log_path

    def start(self) -> RunStatus:
        self._transition_to(RunStatus.LAUNCHING)
        self._transition_to(RunStatus.PROFILING)
        self._transition_to(RunStatus.RUNNING)
        self.logger.log("run_started", self.status)
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

    def _transition_to(self, next_status: RunStatus) -> None:
        self.status = self.lifecycle.transition(self.status, next_status)
