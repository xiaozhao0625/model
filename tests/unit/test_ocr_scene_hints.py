from __future__ import annotations

from ai_screenshot_platform.common.ocr.ocr_scene_hints import OcrSceneHintExtractor


def test_scene_hints_include_login_captcha_and_payment():
    hints = OcrSceneHintExtractor().extract("登录 验证码 支付 订单")

    assert "login" in hints
    assert "captcha" in hints
    assert "payment" in hints
    assert "purchase" in hints
