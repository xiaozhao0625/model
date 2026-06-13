from __future__ import annotations

from ai_screenshot_platform.common.scene_classification.rule_classifier import RuleSceneClassifier


def test_scene_classifier_uses_ocr_hints_and_metadata():
    classifier = RuleSceneClassifier()

    assert classifier.classify({"ocr_scene_hints": ["captcha"]}).scene_class == "captcha"
    assert classifier.classify({"url": "https://example.com"}).scene_class == "browser_page"
