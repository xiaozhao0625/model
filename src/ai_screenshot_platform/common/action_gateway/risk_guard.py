from __future__ import annotations

from ai_screenshot_platform.common.ocr.risk_lexicon import OcrRiskLexicon


class TextRiskGuard:
    def detect(self, text: str) -> list[str]:
        return [hit.risk_type for hit in OcrRiskLexicon.default().detect(text)]
