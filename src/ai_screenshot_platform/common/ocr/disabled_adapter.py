from __future__ import annotations

from ai_screenshot_platform.common.ocr.contracts import (
    OcrAdapter,
    OcrInput,
    OcrProviderStatus,
    OcrResult,
)


class DisabledOcrAdapter(OcrAdapter):
    provider_name = "disabled"

    def run_ocr(self, ocr_input: OcrInput) -> OcrResult:
        return OcrResult(
            provider=self.provider_name,
            available=False,
            status=OcrProviderStatus.SKIPPED,
            error_reason="ocr_disabled",
        )
