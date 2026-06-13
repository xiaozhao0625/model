from __future__ import annotations

from ai_screenshot_platform.common.capture_engine.contracts import (
    CaptureBucketDecision,
    CaptureDecisionInput,
)


class CaptureBucketDecider:
    rejected_scenes = {"captcha", "payment", "recharge", "purchase", "account_security"}

    def decide(self, decision_input: CaptureDecisionInput) -> CaptureBucketDecision:
        if not decision_input.quality_accepted:
            return CaptureBucketDecision("rejected", False, decision_input.reject_reason, "quality_rejected")
        if decision_input.scene_class in self.rejected_scenes:
            return CaptureBucketDecision("rejected", False, "dangerous_page", "risky_scene")
        if decision_input.fixed_candidate:
            return CaptureBucketDecision("fixed", True, reason="fixed_candidate")
        if decision_input.app_type == "game" or decision_input.profile_bucket == "high":
            return CaptureBucketDecision("high", True, reason="game_or_high_profile")
        return CaptureBucketDecision("low", True, reason="default_low")
