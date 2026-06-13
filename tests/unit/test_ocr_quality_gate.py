from __future__ import annotations

from ai_screenshot_platform.common.ocr.contracts import OcrResult, OcrRiskHit
from ai_screenshot_platform.common.ocr.ocr_quality_gate import (
    OcrBrowserChromeDetector,
    OcrDangerousPageDetector,
    OcrQualityGate,
)


def test_ocr_dangerous_page_detector_rejects_payment():
    result = OcrResult(
        provider="mock",
        available=True,
        risk_hits=[OcrRiskHit(risk_type="payment", matched_text="支付", action="reject")],
    )

    decision = OcrDangerousPageDetector().detect(result)

    assert decision.reject is True
    assert decision.reject_reason == "dangerous_page"


def test_ocr_unavailable_does_not_fail_quality_gate():
    decision = OcrQualityGate().evaluate(OcrResult(provider="disabled", available=False))

    assert decision.reject is False
    assert decision.ocr_text_detected is False
    assert decision.ocr_unavailable_reason == "ocr_unavailable"


def test_browser_chrome_detector_flags_address_bar_text():
    result = OcrResult(provider="mock", available=True, full_text="https://example.com 标签页")

    assert OcrBrowserChromeDetector().detect(result) is True
