from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.worker.behavior_worker import BehaviorWorkerAgent
from ai_screenshot_platform.common.worker.contracts import (
    WorkerCapability,
    WorkerProfile,
    WorkerResult,
    WorkerTask,
    WorkerType,
)
from ai_screenshot_platform.common.worker.mock_worker import MockWorkerAgent
from ai_screenshot_platform.workers.android.contracts import AndroidTargetConfig
from ai_screenshot_platform.workers.android.pipeline import AndroidStubPipeline
from ai_screenshot_platform.workers.android.stub_adapters import (
    StubAndroidDeviceAdapter,
    StubAndroidQualityAdapter,
    StubAndroidUiObserverAdapter,
)
from ai_screenshot_platform.workers.pc_app.contracts import PcAppTargetConfig
from ai_screenshot_platform.workers.pc_app.pipeline import PcAppStubPipeline
from ai_screenshot_platform.workers.pc_app.stub_adapters import (
    StubPcAppAutomationAdapter,
)
from ai_screenshot_platform.workers.pc_game.contracts import CaptureSourceConfig
from ai_screenshot_platform.workers.pc_game.pipeline import PcGameStubPipeline
from ai_screenshot_platform.workers.pc_game.stub_adapters import (
    StubFfmpegExtractAdapter,
    StubGameInputAdapter,
    StubObsCaptureAdapter,
)
from ai_screenshot_platform.workers.web.contracts import WebTargetConfig
from ai_screenshot_platform.workers.web.pipeline import WebStubPipeline
from ai_screenshot_platform.workers.web.stub_adapters import StubWebAutomationAdapter


class ExecutorResolver:
    supported_modes = {
        "mock",
        "pc_game_stub",
        "pc_game_behavior",
        "pc_app_stub",
        "web_stub",
        "android_stub",
    }

    def execute(
        self,
        execution_mode: str,
        task: WorkerTask,
        profile: WorkerProfile | None = None,
    ) -> WorkerResult:
        if execution_mode not in self.supported_modes:
            raise ValueError(f"unsupported execution_mode: {execution_mode}")

        worker_profile = profile or self._default_profile(execution_mode)
        if execution_mode == "mock":
            return MockWorkerAgent(worker_profile).execute(task)
        if execution_mode == "pc_game_behavior":
            return BehaviorWorkerAgent(worker_profile).execute(task)
        if execution_mode == "pc_game_stub":
            return self._run_pc_game_stub(task)
        if execution_mode == "pc_app_stub":
            return self._run_pc_app_stub(task)
        if execution_mode == "web_stub":
            return self._run_web_stub(task)
        if execution_mode == "android_stub":
            return self._run_android_stub(task)

        raise ValueError(f"unsupported execution_mode: {execution_mode}")

    def result_to_payload(self, result: WorkerResult) -> dict[str, Any]:
        payload = asdict(result)
        payload["status"] = result.status.value
        payload["run_dir"] = str(result.run_dir)
        payload["summary_path"] = str(result.summary_path)
        if result.behavior_actions_path is not None:
            payload["behavior_actions_path"] = str(result.behavior_actions_path)
        return payload

    def _run_pc_game_stub(self, task: WorkerTask) -> WorkerResult:
        session = self._make_session(task)
        result = PcGameStubPipeline(
            session,
            StubObsCaptureAdapter(session.run_dir / "temp_video"),
            StubFfmpegExtractAdapter(),
            StubGameInputAdapter(),
        ).run(
            CaptureSourceConfig(
                source_name=task.run_id,
                window_title=task.app_id,
                fps=30,
                width=1280,
                height=720,
            ),
            max_frames=task.target_min,
        )
        return self._pipeline_result_to_worker_result(task, result)

    def _run_pc_app_stub(self, task: WorkerTask) -> WorkerResult:
        session = self._make_session(task)
        result = PcAppStubPipeline(
            session=session,
            automation_adapter=StubPcAppAutomationAdapter(),
        ).run(
            PcAppTargetConfig(
                app_id=task.app_id,
                window_title=task.app_id,
                process_name=f"{task.app_id}.exe",
                content_region={"x": 0, "y": 0, "width": 1280, "height": 720},
                bucket=Bucket(task.bucket),
            )
        )
        return self._pipeline_result_to_worker_result(task, result)

    def _run_web_stub(self, task: WorkerTask) -> WorkerResult:
        session = self._make_session(task)
        result = WebStubPipeline(
            session=session,
            automation_adapter=StubWebAutomationAdapter(),
        ).run(
            WebTargetConfig(
                app_id=task.app_id,
                url=f"https://example.invalid/{task.app_id}",
                viewport_width=1280,
                viewport_height=720,
                content_area_only=True,
                bucket=Bucket(task.bucket),
            )
        )
        return self._pipeline_result_to_worker_result(task, result)

    def _run_android_stub(self, task: WorkerTask) -> WorkerResult:
        session = self._make_session(task)
        result = AndroidStubPipeline(
            session=session,
            device_adapter=StubAndroidDeviceAdapter(),
            ui_observer=StubAndroidUiObserverAdapter(),
            quality_adapter=StubAndroidQualityAdapter(),
        ).run(
            AndroidTargetConfig(
                app_id=task.app_id,
                package_name=f"local.mock.{task.app_id}",
                activity_name=".MainActivity",
                device_id="mock-device",
                bucket=Bucket(task.bucket),
            )
        )
        return self._pipeline_result_to_worker_result(task, result)

    def _pipeline_result_to_worker_result(self, task: WorkerTask, result) -> WorkerResult:
        return WorkerResult(
            app_id=task.app_id,
            run_id=task.run_id,
            status=result.status,
            valid_total=result.valid_total,
            fixed_count=result.fixed_count,
            low_count=result.low_count,
            high_count=result.high_count,
            rejected_count=result.rejected_count,
            run_dir=result.run_dir,
            summary_path=result.summary_path,
            error=result.error,
        )

    def _make_session(self, task: WorkerTask) -> LocalRunSession:
        return LocalRunSession(
            RunSessionConfig(
                root_dir=task.root_dir,
                app_id=task.app_id,
                run_id=task.run_id,
                target_min=task.target_min,
                target_max=task.target_max,
            )
        )

    def _default_profile(self, execution_mode: str) -> WorkerProfile:
        worker_type = WorkerType.MOCK
        capabilities = {WorkerCapability.CAPTURE_LOW}
        if execution_mode in {"pc_game_stub", "pc_game_behavior"}:
            worker_type = WorkerType.PC_GAME
            capabilities = {
                WorkerCapability.CAPTURE_HIGH,
                WorkerCapability.BEHAVIOR_PACK,
                WorkerCapability.OBS_CAPTURE,
                WorkerCapability.FFMPEG_EXTRACT,
            }
        return WorkerProfile(
            worker_id=f"{execution_mode}_worker",
            machine_name="local-dev",
            worker_type=worker_type,
            gpu_name=None,
            capabilities=capabilities,
        )
