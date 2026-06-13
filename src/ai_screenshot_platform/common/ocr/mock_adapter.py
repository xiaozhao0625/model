from __future__ import annotations

from ai_screenshot_platform.common.ocr.contracts import (
    OcrAdapter,
    OcrInput,
    OcrResult,
    OcrTextBlock,
)
from ai_screenshot_platform.common.ocr.ocr_scene_hints import OcrSceneHintExtractor
from ai_screenshot_platform.common.ocr.risk_lexicon import OcrRiskLexicon


class MockOcrAdapter(OcrAdapter):
    provider_name = "mock"

    def __init__(self, mock_text: str | None = None) -> None:
        self.mock_text = mock_text or "mock text"

    def run_ocr(self, ocr_input: OcrInput) -> OcrResult:
        text = str(ocr_input.metadata.get("mock_text") or self.mock_text)
        return OcrResult(
            provider=self.provider_name,
            available=True,
            text_blocks=[OcrTextBlock(text=text, source=self.provider_name)],
            full_text=text,
            risk_hits=OcrRiskLexicon.default().detect(text),
            scene_hints=OcrSceneHintExtractor().extract(text),
        )
