from __future__ import annotations

from ai_screenshot_platform.common.quality_gate.contracts import (
    ScreenshotQualityInput,
    ScreenshotQualityResult,
)
from ai_screenshot_platform.common.quality_gate import reject_reasons


class ImageQualityGate:
    min_width = 320
    min_height = 240

    def evaluate(self, quality_input: ScreenshotQualityInput) -> ScreenshotQualityResult:
        data = quality_input.image_bytes
        if data is None and quality_input.image_path and quality_input.image_path.exists():
            data = quality_input.image_path.read_bytes()
        if not data:
            return ScreenshotQualityResult(
                image_id=quality_input.image_id,
                accepted=False,
                reject_reason=reject_reasons.DETECTOR_UNAVAILABLE,
                quality_score=0.0,
            )
        if len(set(data[: min(len(data), 256)])) == 1:
            value = data[0]
            if value == 0:
                return ScreenshotQualityResult(
                    image_id=quality_input.image_id,
                    accepted=False,
                    reject_reason=reject_reasons.BLACK_SCREEN,
                    quality_score=0.0,
                    is_black_screen=True,
                )
            if value == 255:
                return ScreenshotQualityResult(
                    image_id=quality_input.image_id,
                    accepted=False,
                    reject_reason=reject_reasons.WHITE_SCREEN,
                    quality_score=0.0,
                    is_white_screen=True,
                )
        width = int(quality_input.metadata.get("width", self.min_width))
        height = int(quality_input.metadata.get("height", self.min_height))
        if width < self.min_width or height < self.min_height:
            return ScreenshotQualityResult(
                image_id=quality_input.image_id,
                accepted=False,
                reject_reason=reject_reasons.LOW_RESOLUTION,
                quality_score=0.3,
                resolution_ok=False,
            )
        if float(quality_input.metadata.get("blur_score", 1.0)) < 0.2:
            return ScreenshotQualityResult(
                image_id=quality_input.image_id,
                accepted=False,
                reject_reason=reject_reasons.BLURRY,
                quality_score=0.4,
                is_blurry=True,
            )
        return ScreenshotQualityResult(image_id=quality_input.image_id, accepted=True)
