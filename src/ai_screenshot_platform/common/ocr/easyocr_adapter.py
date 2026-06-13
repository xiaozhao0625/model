from __future__ import annotations

import importlib.util

from ai_screenshot_platform.common.ocr.contracts import (
    OcrAdapter,
    OcrInput,
    OcrProviderStatus,
    OcrResult,
)


class EasyOcrOptionalAdapter(OcrAdapter):
    provider_name = "easyocr"

    def run_ocr(self, ocr_input: OcrInput) -> OcrResult:
        if importlib.util.find_spec("easyocr") is None:
            return OcrResult(
                provider=self.provider_name,
                available=False,
                status=OcrProviderStatus.UNAVAILABLE,
                error_reason="easyocr_not_installed",
            )
        return OcrResult(
            provider=self.provider_name,
            available=False,
            status=OcrProviderStatus.UNAVAILABLE,
            error_reason="easyocr_optional_adapter_not_enabled",
        )
