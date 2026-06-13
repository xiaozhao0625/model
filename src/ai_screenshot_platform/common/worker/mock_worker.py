from __future__ import annotations

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.worker.contracts import (
    WorkerProfile,
    WorkerResult,
    WorkerState,
    WorkerTask,
)


class MockWorkerAgent:
    def __init__(self, profile: WorkerProfile) -> None:
        self.profile = profile

    def execute(self, task: WorkerTask) -> WorkerResult:
        self.profile.state = WorkerState.RUNNING
        self.profile.current_run_id = task.run_id
        session = LocalRunSession(
            RunSessionConfig(
                root_dir=task.root_dir,
                app_id=task.app_id,
                run_id=task.run_id,
                target_min=task.target_min,
                target_max=task.target_max,
            )
        )

        try:
            session.start()
            bucket = Bucket(task.bucket)
            for index in range(task.target_min):
                session.save_image(
                    bucket=bucket,
                    image_bytes=f"{task.app_id}:{task.run_id}:{index}".encode("utf-8"),
                )
            session.evaluate_completion()
            summary = session.generate_summary()
            self.profile.state = WorkerState.STOPPED
            self.profile.current_run_id = None
            return WorkerResult(
                app_id=task.app_id,
                run_id=task.run_id,
                status=session.status,
                valid_total=int(summary["valid_total"]),
                fixed_count=int(summary["fixed_count"]),
                low_count=int(summary["low_count"]),
                high_count=int(summary["high_count"]),
                rejected_count=int(summary["rejected_count"]),
                run_dir=session.run_dir,
                summary_path=session.run_dir / "summary.json",
            )
        except Exception as exc:
            self.profile.state = WorkerState.FAILED
            return WorkerResult(
                app_id=task.app_id,
                run_id=task.run_id,
                status=session.status,
                valid_total=0,
                fixed_count=0,
                low_count=0,
                high_count=0,
                rejected_count=0,
                run_dir=session.run_dir,
                summary_path=session.run_dir / "summary.json",
                error=str(exc),
            )
