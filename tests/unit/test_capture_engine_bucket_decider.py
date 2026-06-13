from __future__ import annotations

from ai_screenshot_platform.common.capture_engine.bucket_decider import CaptureBucketDecider
from ai_screenshot_platform.common.capture_engine.contracts import CaptureDecisionInput


def test_bucket_decider_rejects_bad_quality_and_routes_game_high():
    decider = CaptureBucketDecider()

    rejected = decider.decide(CaptureDecisionInput(quality_accepted=False, reject_reason="black_screen"))
    high = decider.decide(CaptureDecisionInput(app_type="game", scene_class="combat", profile_bucket="high"))

    assert rejected.bucket == "rejected"
    assert rejected.reject_reason == "black_screen"
    assert high.bucket == "high"
