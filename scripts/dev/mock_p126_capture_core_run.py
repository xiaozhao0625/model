from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.action_gateway.contracts import ActionGatewayRequest  # noqa: E402
from ai_screenshot_platform.common.action_gateway.execution_guard import ActionGateway  # noqa: E402
from ai_screenshot_platform.common.capture_engine.capture_engine import CaptureEngine  # noqa: E402
from ai_screenshot_platform.common.capture_engine.contracts import CaptureDecisionInput  # noqa: E402
from ai_screenshot_platform.common.content_drivers.web_content_driver import WebContentDriver  # noqa: E402
from ai_screenshot_platform.common.runtime_profiler.profiler import RuntimeProfiler  # noqa: E402
from ai_screenshot_platform.common.scene_classification.rule_classifier import RuleSceneClassifier  # noqa: E402


def main() -> None:
    profile = RuntimeProfiler().profile({"platform_type": "web", "worker_type": "web"})
    scene = RuleSceneClassifier().classify({"ocr_scene_hints": ["browser_page"]})
    bucket = CaptureEngine().decide(CaptureDecisionInput(scene_class=scene.scene_class, profile_bucket=profile.recommended_bucket))
    safe_action = ActionGateway().evaluate(ActionGatewayRequest(action_type="wait", instruction="等待"))
    risky_action = ActionGateway().evaluate(ActionGatewayRequest(action_type="click", instruction="确认支付"))
    plan = WebContentDriver().plan({"url": "https://example.com"})
    print(
        json.dumps(
            {
                "runtime_bucket": profile.recommended_bucket,
                "scene_class": scene.scene_class,
                "bucket": bucket.bucket,
                "safe_action_allowed": safe_action.allowed,
                "risky_action_allowed": risky_action.allowed,
                "content_driver_steps": [step.action_type for step in plan.steps],
                "real_action_executed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
