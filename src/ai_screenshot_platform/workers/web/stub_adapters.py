from __future__ import annotations

from ai_screenshot_platform.workers.web.contracts import (
    WebCapturedFrame,
    WebCommand,
    WebCommandResult,
    WebTargetConfig,
)


class StubWebAutomationAdapter:
    def open_target(self, config: WebTargetConfig) -> WebCommandResult:
        return WebCommandResult(
            command_id=f"open:{config.app_id}",
            executed=False,
            skipped=True,
            reason="stub adapter skipped real browser open",
        )

    def execute(self, command: WebCommand) -> WebCommandResult:
        return WebCommandResult(
            command_id=command.command_id,
            executed=False,
            skipped=True,
            reason="stub adapter skipped real web command",
        )

    def capture_frame(self, config: WebTargetConfig) -> WebCapturedFrame:
        return WebCapturedFrame(
            frame_id=f"web-stub-{config.app_id}",
            image_bytes=(
                f"web_stub:{config.app_id}:{config.url}:"
                f"{config.viewport_width}x{config.viewport_height}:"
                f"content_area_only={config.content_area_only}"
            ).encode("utf-8"),
            bucket=config.bucket,
            source="web_stub",
            content_area_only=config.content_area_only,
        )
