from __future__ import annotations

from ai_screenshot_platform.workers.runtime.health import ToolHealth
from ai_screenshot_platform.workers.web.contracts import (
    WebCapturedFrame,
    WebCommand,
    WebCommandResult,
    WebTargetConfig,
)
from ai_screenshot_platform.workers.web.health_check import (
    check_web_playwright_health,
)


class RealPlaywrightWebAdapter:
    def __init__(self, enabled: bool = False, headless: bool = True) -> None:
        self.enabled = enabled
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None

    def health(self) -> ToolHealth:
        if not self.enabled:
            return ToolHealth(
                name="playwright",
                available=False,
                version=None,
                reason="disabled by config",
                required_for="web real capture smoke",
            )
        return check_web_playwright_health()

    def open_target(self, config: WebTargetConfig) -> WebCommandResult:
        health = self.health()
        if not health.available:
            return WebCommandResult(
                command_id=f"open:{config.app_id}",
                executed=False,
                skipped=True,
                reason=health.reason,
            )
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page(
            viewport={
                "width": config.viewport_width,
                "height": config.viewport_height,
            }
        )
        self._page.goto(config.url)
        return WebCommandResult(
            command_id=f"open:{config.app_id}",
            executed=True,
            skipped=False,
            reason="opened with playwright",
        )

    def execute(self, command: WebCommand) -> WebCommandResult:
        if command.command_type == "wait" and self._page is not None:
            self._page.wait_for_timeout(int(command.params.get("duration_ms", 100)))
            return WebCommandResult(
                command_id=command.command_id,
                executed=True,
                skipped=False,
                reason="wait executed in page context",
            )
        return WebCommandResult(
            command_id=command.command_id,
            executed=False,
            skipped=True,
            reason="real web adapter only supports safe wait command in P10",
        )

    def capture_frame(self, config: WebTargetConfig) -> WebCapturedFrame:
        health = self.health()
        if not health.available:
            raise RuntimeError(f"playwright unavailable: {health.reason}")
        if self._page is None:
            self.open_target(config)
        image_bytes = self._page.locator("body").screenshot()
        return WebCapturedFrame(
            frame_id=f"playwright-web-{config.app_id}",
            image_bytes=image_bytes,
            bucket=config.bucket,
            source="playwright_content_area",
            content_area_only=config.content_area_only,
        )

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None
