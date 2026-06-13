from __future__ import annotations

from ai_screenshot_platform.common.quality_gate.contracts import (
    ScreenshotQualityInput,
    ScreenshotQualityResult,
)
from ai_screenshot_platform.common.quality_gate import reject_reasons


class BrowserContentGate:
    def evaluate(self, quality_input: ScreenshotQualityInput) -> ScreenshotQualityResult:
        browser_chrome = bool(quality_input.metadata.get("browser_chrome_visible"))
        taskbar = bool(quality_input.metadata.get("taskbar_visible"))
        title_bar = bool(quality_input.metadata.get("title_bar_visible"))
        if browser_chrome:
            return ScreenshotQualityResult(
                image_id=quality_input.image_id,
                accepted=False,
                reject_reason=reject_reasons.BROWSER_CHROME_VISIBLE,
                has_browser_chrome=True,
            )
        if taskbar:
            return ScreenshotQualityResult(
                image_id=quality_input.image_id,
                accepted=False,
                reject_reason=reject_reasons.OS_TASKBAR_VISIBLE,
                has_os_taskbar=True,
            )
        if title_bar:
            return ScreenshotQualityResult(
                image_id=quality_input.image_id,
                accepted=False,
                reject_reason=reject_reasons.TITLE_BAR_VISIBLE,
                has_title_bar=True,
            )
        if quality_input.worker_type == "web" and not quality_input.content_area_only:
            return ScreenshotQualityResult(
                image_id=quality_input.image_id,
                accepted=False,
                reject_reason=reject_reasons.BROWSER_CHROME_VISIBLE,
                has_browser_chrome=True,
            )
        return ScreenshotQualityResult(image_id=quality_input.image_id, accepted=True)
