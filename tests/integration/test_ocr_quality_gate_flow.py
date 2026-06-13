from __future__ import annotations

from ai_screenshot_platform.common.ocr.contracts import OcrInput
from ai_screenshot_platform.common.ocr.ocr_quality_gate import OcrQualityGate
from ai_screenshot_platform.common.ocr.router import OcrRouter


def test_mock_ocr_risk_flows_into_quality_gate_rejection():
    router = OcrRouter.from_policy({"default_provider": "mock", "mock_text": "验证码 支付"})
    ocr_result = router.run_ocr(OcrInput(image_bytes=b"mock"))
    quality = OcrQualityGate().evaluate(ocr_result)

    assert quality.reject is True
    assert quality.reject_reason == "dangerous_page"
    assert quality.ocr_risk_hit_count >= 2
