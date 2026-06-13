from __future__ import annotations

import json
from pathlib import Path

from ai_screenshot_platform.common.ocr.contracts import OcrAdapter, OcrInput, OcrResult
from ai_screenshot_platform.common.ocr.disabled_adapter import DisabledOcrAdapter
from ai_screenshot_platform.common.ocr.easyocr_adapter import EasyOcrOptionalAdapter
from ai_screenshot_platform.common.ocr.mock_adapter import MockOcrAdapter
from ai_screenshot_platform.common.ocr.ocr_scene_hints import OcrSceneHintExtractor
from ai_screenshot_platform.common.ocr.paddle_adapter import PaddleOcrOptionalAdapter
from ai_screenshot_platform.common.ocr.risk_lexicon import OcrRiskLexicon


class OcrRouter:
    def __init__(self, adapter: OcrAdapter) -> None:
        self.adapter = adapter

    @classmethod
    def from_policy(cls, policy: dict | str | Path | None = None) -> OcrRouter:
        if policy is None:
            payload = {"default_provider": "disabled"}
        elif isinstance(policy, dict):
            payload = policy
        else:
            payload = json.loads(Path(policy).read_text(encoding="utf-8"))
        provider = str(payload.get("default_provider", "disabled"))
        if provider == "mock":
            return cls(MockOcrAdapter(mock_text=payload.get("mock_text")))
        if provider == "paddleocr":
            return cls(PaddleOcrOptionalAdapter())
        if provider == "easyocr":
            return cls(EasyOcrOptionalAdapter())
        return cls(DisabledOcrAdapter())

    def run_ocr(self, ocr_input: OcrInput) -> OcrResult:
        return self.adapter.run_ocr(ocr_input)

    def detect_risk(self, result: OcrResult):
        return OcrRiskLexicon.default().detect(result.full_text)

    def extract_scene_hints(self, result: OcrResult) -> list[str]:
        return OcrSceneHintExtractor().extract(result.full_text)
