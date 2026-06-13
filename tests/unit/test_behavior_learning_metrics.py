from __future__ import annotations

from ai_screenshot_platform.common.behavior_learning.inputs import BehaviorLearningSnapshot
from ai_screenshot_platform.common.behavior_learning.metrics import BehaviorMetricsCalculator
from ai_screenshot_platform.common.behavior_learning.fps_analyzer import FpsBehaviorAnalyzer
from ai_screenshot_platform.common.behavior_learning.moba_analyzer import MobaBehaviorAnalyzer


def make_snapshot() -> BehaviorLearningSnapshot:
    return BehaviorLearningSnapshot(
        summary={
            "valid_total": 10,
            "fixed_count": 0,
            "low_count": 2,
            "high_count": 8,
            "rejected_count": 5,
        },
        meta_rows=[
            {"valid": True, "content_hash": str(index)}
            for index in range(10)
        ]
        + [
            {"valid": False, "reject_reason": "duplicate_content_hash"}
            for _ in range(5)
        ],
        run_events=[
            {"event": "manual_seed_requested"},
            {"event": "failed_low_yield"},
            {"event": "duplicate_rejected"},
        ],
        behavior_actions=[
            {"action_type": "move", "skipped": False, "risk_flags": []},
            {"action_type": "camera", "skipped": False, "risk_flags": []},
            {"action_type": "capture_hint", "skipped": False, "risk_flags": []},
            {"action_type": "recovery", "skipped": True, "risk_flags": ["stuck"]},
        ],
    )


def test_behavior_metrics_calculates_common_ratios():
    metrics = BehaviorMetricsCalculator().calculate(make_snapshot())

    assert metrics.valid_total == 10
    assert metrics.duplicate_ratio == 0.5
    assert metrics.valid_yield == 10 / 15
    assert metrics.saved_images_per_action == 2.5
    assert metrics.manual_seed_count == 1
    assert metrics.failed_low_yield is True


def test_fps_analyzer_generates_duplicate_stuck_and_death_loop_issues():
    metrics = BehaviorMetricsCalculator().calculate(make_snapshot())
    analysis = FpsBehaviorAnalyzer().analyze(metrics)

    assert "duplicate_ratio_high" in analysis.issues
    assert "stuck_ratio_high" in analysis.issues
    assert "death_loop_high" in analysis.issues
    assert any("转向" in item or "recover" in item for item in analysis.recommendations)


def test_moba_analyzer_generates_base_and_skill_recommendations():
    metrics = BehaviorMetricsCalculator().calculate(make_snapshot())
    analysis = MobaBehaviorAnalyzer().analyze(metrics)

    assert "base_stuck_detected" in analysis.issues
    assert "skill_usage_low" in analysis.issues
    assert any("技能" in item or "出门" in item for item in analysis.recommendations)
