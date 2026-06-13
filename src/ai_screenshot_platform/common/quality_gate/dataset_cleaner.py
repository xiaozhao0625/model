from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.common.ocr.contracts import OcrInput
from ai_screenshot_platform.common.ocr.ocr_quality_gate import OcrQualityGate
from ai_screenshot_platform.common.ocr.router import OcrRouter
from ai_screenshot_platform.common.quality_gate.browser_content_gate import BrowserContentGate
from ai_screenshot_platform.common.quality_gate.contracts import (
    ScreenshotQualityInput,
    ScreenshotQualityResult,
)
from ai_screenshot_platform.common.quality_gate.image_quality import ImageQualityGate
from ai_screenshot_platform.common.quality_gate.report import QualityReportPaths, QualityReportWriter


class DatasetCleaner:
    def __init__(self, output_dir: str | Path, ocr_router: OcrRouter | None = None) -> None:
        self.output_dir = Path(output_dir)
        self.ocr_router = ocr_router or OcrRouter.from_policy({"default_provider": "disabled"})

    def clean(self, inputs: list[ScreenshotQualityInput]) -> QualityReportPaths:
        results = [self._evaluate(item) for item in inputs]
        return QualityReportWriter().write(self.output_dir, results)

    def _evaluate(self, item: ScreenshotQualityInput) -> ScreenshotQualityResult:
        image_result = ImageQualityGate().evaluate(item)
        if not image_result.accepted:
            return image_result
        browser_result = BrowserContentGate().evaluate(item)
        if not browser_result.accepted:
            return browser_result
        ocr_result = item.ocr_result
        if ocr_result is None and item.metadata.get("ocr_text"):
            ocr_result = OcrRouter.from_policy(
                {"default_provider": "mock", "mock_text": str(item.metadata["ocr_text"])}
            ).run_ocr(OcrInput(image_bytes=item.image_bytes, metadata=item.metadata))
        if ocr_result is None:
            ocr_result = self.ocr_router.run_ocr(OcrInput(image_bytes=item.image_bytes, metadata=item.metadata))
        ocr_decision = OcrQualityGate().evaluate(ocr_result)
        if ocr_decision.reject:
            return ScreenshotQualityResult(
                image_id=item.image_id,
                accepted=False,
                reject_reason=ocr_decision.reject_reason,
                ocr_risk_hit_count=ocr_decision.ocr_risk_hit_count,
            )
        return image_result
