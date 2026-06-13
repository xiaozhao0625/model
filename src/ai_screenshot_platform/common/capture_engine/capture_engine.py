from __future__ import annotations

from ai_screenshot_platform.common.capture_engine.bucket_decider import CaptureBucketDecider
from ai_screenshot_platform.common.capture_engine.contracts import (
    CaptureBucketDecision,
    CaptureDecisionInput,
)


class CaptureEngine:
    def __init__(self, decider: CaptureBucketDecider | None = None) -> None:
        self.decider = decider or CaptureBucketDecider()

    def decide(self, decision_input: CaptureDecisionInput) -> CaptureBucketDecision:
        return self.decider.decide(decision_input)
