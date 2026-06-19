from __future__ import annotations

from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.schemas import OcrResult, ProviderHealth


class PaddleOcrProvider(OcrProvider):
    provider_name = "paddleocr"

    def __init__(self) -> None:
        self._paddleocr_cls = None
        self._error: str | None = None
        try:
            from paddleocr import PaddleOCR  # type: ignore

            self._paddleocr_cls = PaddleOCR
        except Exception as exc:  # Optional runtime dependency.
            self._error = str(exc)

    def health(self) -> ProviderHealth:
        if self._paddleocr_cls is None:
            return ProviderHealth(
                provider=self.provider_name,
                status="unavailable",
                enabled=False,
                reason="paddleocr_not_installed",
                details={"error": self._error},
            )
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=False, reason="available_but_disabled_by_default")

    def recognize(self, image_path: str) -> OcrResult:
        if self._paddleocr_cls is None:
            return OcrResult(provider=self.provider_name, status="unavailable", error="paddleocr_not_installed")
        return OcrResult(
            provider=self.provider_name,
            status="unavailable",
            error="real PaddleOCR inference is wired but disabled until model/runtime is explicitly enabled",
        )
