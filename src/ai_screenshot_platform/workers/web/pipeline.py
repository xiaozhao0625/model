from __future__ import annotations

from ai_screenshot_platform.common.runtime.run_session import LocalRunSession
from ai_screenshot_platform.workers.web.contracts import (
    WebAutomationAdapter,
    WebCommand,
    WebPipelineResult,
    WebTargetConfig,
)


class WebStubPipeline:
    def __init__(
        self,
        session: LocalRunSession,
        automation_adapter: WebAutomationAdapter,
    ) -> None:
        self.session = session
        self.automation_adapter = automation_adapter

    def run(self, config: WebTargetConfig) -> WebPipelineResult:
        command_results = [
            self.automation_adapter.open_target(config),
            self.automation_adapter.execute(
                WebCommand(
                    command_id="web_stub_wait",
                    command_type="wait",
                    description="Stub wait command; no real browser action is executed.",
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

        return WebPipelineResult(
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
            content_area_only=config.content_area_only,
        )

    def _unique_frame_bytes(self, image_bytes: bytes, index: int) -> bytes:
        return image_bytes + f":{self.session.config.run_id}:{index}".encode("utf-8")
