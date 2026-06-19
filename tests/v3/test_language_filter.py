from ai_screenshot_platform.v3.ocr.language_filter import filter_language


def test_language_filter_accepts_target_script():
    assert filter_language("开始", "zh").accepted
    assert filter_language("Start", "en").accepted
    assert filter_language("開始", "ja").accepted
    assert filter_language("시작", "ko").accepted


def test_language_filter_rejects_wrong_language():
    result = filter_language("Start", "zh")
    assert not result.accepted
    assert result.reason == "wrong_language"


def test_language_filter_rejects_non_target_ja_ko():
    assert filter_language("開始", "en").reason == "wrong_language"
    assert filter_language("시작", "ja").reason == "wrong_language"
    assert filter_language("開始", "ko").reason == "wrong_language"


def test_language_filter_rejects_mixed_language_text():
    result = filter_language("Start 開始 시작", "en")
    assert not result.accepted
    assert result.reason == "mixed_language"


def test_language_filter_rejects_single_target_character_noise():
    result = filter_language("7가<", "ko")
    assert not result.accepted
    assert result.reason == "too_few_chars"
