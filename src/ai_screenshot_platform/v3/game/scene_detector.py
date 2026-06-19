from __future__ import annotations

from ai_screenshot_platform.v3.schemas import OcrResult, SceneClassification


def classify_game_scene(ocr_result: OcrResult | None, visual_changed: bool = False) -> SceneClassification:
    text = " ".join(box.text for box in (ocr_result.text_boxes if ocr_result else []))
    lowered = text.lower()
    if any(term in lowered for term in ["login", "password", "验证码", "支付"]):
        return SceneClassification(scene_class="unsafe_page", confidence=0.85, reason="risk_text_detected")
    if visual_changed and not text:
        return SceneClassification(scene_class="game_in_match", confidence=0.6, reason="visual_change_without_text")
    if text:
        return SceneClassification(scene_class="game_menu", confidence=0.55, reason="text_menu_like")
    return SceneClassification(scene_class="game_unknown", confidence=0.3, reason="insufficient_signal")
