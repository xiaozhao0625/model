from __future__ import annotations

from ai_screenshot_platform.common.quality_gate.contracts import ScreenshotQualityInput
from ai_screenshot_platform.common.quality_gate.image_quality import ImageQualityGate


def test_detects_black_white_and_low_resolution():
    gate = ImageQualityGate()

    black = gate.evaluate(ScreenshotQualityInput(image_id="b", image_bytes=b"\x00" * 200))
    white = gate.evaluate(ScreenshotQualityInput(image_id="w", image_bytes=b"\xff" * 200))
    low_res = gate.evaluate(
        ScreenshotQualityInput(image_id="r", image_bytes=b"ok", metadata={"width": 100, "height": 100})
    )

    assert black.reject_reason == "black_screen"
    assert white.reject_reason == "white_screen"
    assert low_res.reject_reason == "low_resolution"


def test_detector_unavailable_is_explicit_for_missing_bytes():
    result = ImageQualityGate().evaluate(ScreenshotQualityInput(image_id="missing"))

    assert result.accepted is False
    assert result.reject_reason == "detector_unavailable"
