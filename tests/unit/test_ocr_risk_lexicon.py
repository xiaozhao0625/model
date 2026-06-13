from __future__ import annotations

from ai_screenshot_platform.common.ocr.risk_lexicon import OcrRiskLexicon


def test_risk_lexicon_detects_chinese_and_english_risks():
    lexicon = OcrRiskLexicon.default()
    text = "请完成验证码 verification 后确认支付 confirm payment，并发送聊天"
    hits = lexicon.detect(text)

    risk_types = {hit.risk_type for hit in hits}
    assert {"captcha", "payment", "chat_send"} <= risk_types


def test_risk_lexicon_keeps_snippets_short():
    hit = OcrRiskLexicon.default().detect("账号安全验证" * 20)[0]

    assert len(hit.matched_text) <= 32
