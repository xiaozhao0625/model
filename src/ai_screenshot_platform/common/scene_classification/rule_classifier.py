from __future__ import annotations

from typing import Any

from ai_screenshot_platform.common.scene_classification.contracts import (
    SceneClassificationResult,
)


class RuleSceneClassifier:
    risky_scenes = {"captcha", "payment", "recharge", "purchase", "account_security"}

    def classify(self, metadata: dict[str, Any]) -> SceneClassificationResult:
        hints = [str(hint) for hint in metadata.get("ocr_scene_hints", [])]
        if hints:
            scene = hints[0]
            return SceneClassificationResult(scene, 0.9, "ocr_hint", hints, metadata)
        if metadata.get("url"):
            return SceneClassificationResult("browser_page", 0.8, "url_present", [], metadata)
        if metadata.get("app_type") == "game":
            return SceneClassificationResult("open_world", 0.6, "game_default", [], metadata)
        return SceneClassificationResult("unknown", 0.2, "no_rule_matched", [], metadata)
