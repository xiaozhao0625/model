from __future__ import annotations

from ai_screenshot_platform.common.runtime.run_session import LocalRunSession
from ai_screenshot_platform.workers.android.contracts import (
    AndroidDeviceAdapter,
    AndroidDeviceCommand,
    AndroidPipelineResult,
    AndroidQualityAdapter,
    AndroidTargetConfig,
    AndroidUiObserverAdapter,
)


class AndroidStubPipeline:
    def __init__(
        self,
        session: LocalRunSession,
        device_adapter: AndroidDeviceAdapter,
        ui_observer: AndroidUiObserverAdapter,
        quality_adapter: AndroidQualityAdapter,
    ) -> None:
        self.session = session
        self.device_adapter = device_adapter
        self.ui_observer = ui_observer
        self.quality_adapter = quality_adapter

    def run(self, config: AndroidTargetConfig) -> AndroidPipelineResult:
        command_results = [
            self.device_adapter.connect(config),
            self.device_adapter.launch_app(config),
            self.device_adapter.execute(
                AndroidDeviceCommand(
                    command_id="android_stub_wait",
                    command_type="wait",
                    description="Stub wait command; no real device action is executed.",
                    params={"duration_ms": 100},
                )
            ),
        ]
        observation = self.ui_observer.observe(config)

        self.session.start()
        quality_results = []
        saved_count = 0
        for index in range(self.session.config.target_min):
            frame = self.device_adapter.capture_frame(config)
            quality = self.quality_adapter.check(frame)
            quality_results.append(quality)
            if quality.valid:
                self.session.save_image(
                    frame.bucket,
                    self._unique_frame_bytes(frame.image_bytes, index),
                )
                saved_count += 1
        self.session.evaluate_completion()
        summary = self.session.generate_summary()

        return AndroidPipelineResult(
            status=self.session.status,
            valid_total=int(summary["valid_total"]),
            fixed_count=int(summary["fixed_count"]),
            low_count=int(summary["low_count"]),
            high_count=int(summary["high_count"]),
            rejected_count=int(summary["rejected_count"]),
            run_dir=self.session.run_dir,
            summary_path=self.session.run_dir / "summary.json",
            captured_frame_count=saved_count,
            command_results=command_results,
            observation=observation,
            quality_results=quality_results,
        )

    def _unique_frame_bytes(self, image_bytes: bytes, index: int) -> bytes:
        return image_bytes + f":{self.session.config.run_id}:{index}".encode("utf-8")
