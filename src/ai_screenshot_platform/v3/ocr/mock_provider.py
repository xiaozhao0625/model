from __future__ import annotations

from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.schemas import OcrResult, OcrTextBox, ProviderHealth


class MockOcrProvider(OcrProvider):
    provider_name = "mock_ocr"

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True, reason="mock provider")

    def recognize(self, image_path: str) -> OcrResult:
        label = "Start" if "start" in image_path.lower() else "OK"
        return OcrResult(
            provider=self.provider_name,
            status="ok",
            text_boxes=[
                OcrTextBox(text=label, bbox=[20, 20, 140, 64], confidence=0.91, language_hint="en"),
            ],
        )
