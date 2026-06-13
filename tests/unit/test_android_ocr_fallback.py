from __future__ import annotations

from ai_screenshot_platform.workers.android.android_ocr_fallback import AndroidOcrFallback


def test_android_ocr_fallback_uses_mock_or_disabled_without_real_ocr():
    result = AndroidOcrFallback(provider="mock", mock_text="账号安全").run_ocr_on_screenshot(b"img")

    assert result.provider == "mock"
    assert result.risk_hits[0].risk_type == "account_security"
