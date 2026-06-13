from __future__ import annotations

import importlib.util

from ai_screenshot_platform.common.ocr.contracts import (
    OcrAdapter,
    OcrInput,
    OcrProviderStatus,
    OcrResult,
)


class PaddleOcrOptionalAdapter(OcrAdapter):
    provider_name = "paddleocr"

    def run_ocr(self, ocr_input: OcrInput) -> OcrResult:
        if importlib.util.find_spec("paddleocr") is None:
            return OcrResult(
                provider=self.provider_name,
                available=False,
                status=OcrProviderStatus.UNAVAILABLE,
                error_reason="paddleocr_not_installed",
            )
        return OcrResult(
            provider=self.provider_name,
            available=False,
            status=OcrProviderStatus.UNAVAILABLE,
            error_reason="paddleocr_optional_adapter_not_enabled",
        )
