from ai_screenshot_platform.v3.ocr.language_filter import filter_language


def test_language_filter_accepts_target_script():
    assert filter_language("开始", "zh").accepted
    assert filter_language("Start", "en").accepted


def test_language_filter_rejects_wrong_language():
    result = filter_language("Start", "zh")
    assert not result.accepted
    assert result.reason == "wrong_language"
