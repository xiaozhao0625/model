from __future__ import annotations

from ai_screenshot_platform.common.runtime.run_session import LocalRunSession
from ai_screenshot_platform.workers.pc_app.contracts import (
    PcAppAutomationAdapter,
    PcAppCommand,
    PcAppPipelineResult,
    PcAppTargetConfig,
)


class PcAppStubPipeline:
    def __init__(
        self,
        session: LocalRunSession,
        automation_adapter: PcAppAutomationAdapter,
    ) -> None:
        self.session = session
        self.automation_adapter = automation_adapter

    def run(self, config: PcAppTargetConfig) -> PcAppPipelineResult:
        command_results = [
            self.automation_adapter.focus_target(config),
            self.automation_adapter.execute(
                PcAppCommand(
                    command_id="pc_app_stub_wait",
                    command_type="wait",
                    description="Stub wait command; no real app action is executed.",
                    params={"duration_ms": 100},
                )
            ),
        ]

        self.session.start()
        for index in range(self.session.config.target_min):
            frame = self.automation_adapter.capture_frame(config)
            self.session.save_image(
                frame.bucket,
                self._unique_frame_bytes(frame.image_bytes, index),
            )
        self.session.evaluate_completion()
        summary = self.session.generate_summary()

        return PcAppPipelineResult(
            status=self.session.status,
            valid_total=int(summary["valid_total"]),
            fixed_count=int(summary["fixed_count"]),
            low_count=int(summary["low_count"]),
            high_count=int(summary["high_count"]),
            rejected_count=int(summary["rejected_count"]),
            run_dir=self.session.run_dir,
            summary_path=self.session.run_dir / "summary.json",
            captured_frame_count=self.session.config.target_min,
            command_results=command_results,
        )

    def _unique_frame_bytes(self, image_bytes: bytes, index: int) -> bytes:
        return image_bytes + f":{self.session.config.run_id}:{index}".encode("utf-8")
