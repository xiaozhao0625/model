from __future__ import annotations

from ai_screenshot_platform.workers.pc_app.contracts import (
    PcAppCapturedFrame,
    PcAppCommand,
    PcAppCommandResult,
    PcAppTargetConfig,
)


class StubPcAppAutomationAdapter:
    def focus_target(self, config: PcAppTargetConfig) -> PcAppCommandResult:
        return PcAppCommandResult(
            command_id=f"focus:{config.app_id}",
            executed=False,
            skipped=True,
            reason="stub adapter skipped real pc app focus",
        )

    def execute(self, command: PcAppCommand) -> PcAppCommandResult:
        return PcAppCommandResult(
            command_id=command.command_id,
            executed=False,
            skipped=True,
            reason="stub adapter skipped real pc app command",
        )

    def capture_frame(self, config: PcAppTargetConfig) -> PcAppCapturedFrame:
        return PcAppCapturedFrame(
            frame_id=f"pc-app-stub-{config.app_id}",
            image_bytes=(
                f"pc_app_stub:{config.app_id}:{config.window_title}:"
                f"{config.content_region}"
            ).encode("utf-8"),
            bucket=config.bucket,
            source="pc_app_stub",
        )
