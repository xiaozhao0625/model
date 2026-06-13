from __future__ import annotations

from ai_screenshot_platform.common.action_gateway.contracts import ActionGatewayRequest
from ai_screenshot_platform.common.action_gateway.execution_guard import ActionGateway
from ai_screenshot_platform.common.capture_engine.capture_engine import CaptureEngine
from ai_screenshot_platform.common.capture_engine.contracts import CaptureDecisionInput
from ai_screenshot_platform.common.runtime_profiler.profiler import RuntimeProfiler
from ai_screenshot_platform.common.scene_classification.rule_classifier import RuleSceneClassifier


def test_capture_core_flow_profiles_classifies_decides_and_blocks_risk():
    profile = RuntimeProfiler().profile({"platform_type": "web", "worker_type": "web"})
    scene = RuleSceneClassifier().classify({"ocr_scene_hints": ["payment"]})
    capture = CaptureEngine().decide(CaptureDecisionInput(scene_class=scene.scene_class, profile_bucket=profile.recommended_bucket))
    action = ActionGateway().evaluate(ActionGatewayRequest(action_type="click", instruction="支付"))

    assert capture.bucket == "rejected"
    assert action.allowed is False
