from __future__ import annotations

from ai_screenshot_platform.common.ocr.contracts import OcrInput
from ai_screenshot_platform.common.ocr.router import OcrRouter


class AndroidOcrFallback:
    def __init__(self, provider: str = "disabled", mock_text: str | None = None) -> None:
        self.router = OcrRouter.from_policy({"default_provider": provider, "mock_text": mock_text})

    def run_ocr_on_screenshot(self, serial_or_image):
        image_bytes = serial_or_image if isinstance(serial_or_image, bytes) else None
        return self.router.run_ocr(OcrInput(image_bytes=image_bytes, metadata={"source": "android_ocr_fallback"}))

    def detect_risk_text(self, serial_or_image):
        return self.run_ocr_on_screenshot(serial_or_image).risk_hits

    def detect_scene_hints(self, serial_or_image):
        return self.run_ocr_on_screenshot(serial_or_image).scene_hints
