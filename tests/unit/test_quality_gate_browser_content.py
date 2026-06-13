from __future__ import annotations

from ai_screenshot_platform.common.quality_gate.browser_content_gate import BrowserContentGate
from ai_screenshot_platform.common.quality_gate.contracts import ScreenshotQualityInput


def test_content_area_only_accepts_clean_web_capture():
    result = BrowserContentGate().evaluate(
        ScreenshotQualityInput(
            image_id="web",
            platform_type="web",
            worker_type="web",
            content_area_only=True,
            metadata={"browser_chrome_visible": False, "taskbar_visible": False},
        )
    )

    assert result.accepted is True


def test_browser_chrome_or_taskbar_is_rejected():
    result = BrowserContentGate().evaluate(
        ScreenshotQualityInput(
            image_id="web",
            platform_type="web",
            worker_type="web",
            content_area_only=False,
            metadata={"browser_chrome_visible": True},
        )
    )

    assert result.accepted is False
    assert result.reject_reason == "browser_chrome_visible"
