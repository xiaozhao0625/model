from __future__ import annotations

import json
from pathlib import Path

from ai_screenshot_platform.common.behavior_learning.analyzer import (
    BehaviorLearningResult,
)
from ai_screenshot_platform.common.behavior_learning.metrics import BehaviorMetrics
from ai_screenshot_platform.common.behavior_learning.recommendation import (
    RecommendationEngine,
)


def test_recommendation_engine_creates_pending_candidate(tmp_path):
    base_pack = json.loads(
        Path("configs/behavior_packs/fps_mock_v1.example.json").read_text(encoding="utf-8")
    )
    result = BehaviorLearningResult(
        run_id="run_001",
        game_type="fps",
        old_behavior_pack_id="fps_mock_v1",
        metrics=BehaviorMetrics(valid_total=10),
        issues=["duplicate_ratio_high", "stuck_ratio_high"],
        recommendations=["增加镜头横向扫描幅度", "增加 recover_if_stuck 动作"],
        should_generate_candidate=True,
        candidate_pack_id=None,
        review_status="pending_review",
    )

    candidate, recommendation = RecommendationEngine().generate_candidate(
        result,
        base_pack,
    )

    assert candidate.status == "pending_review"
    assert candidate.base_pack_id == "fps_mock_v1"
    assert candidate.candidate_pack_id != "fps_mock_v1"
    assert candidate.rollback_target == "fps_mock_v1"
    assert recommendation["review_status"] == "pending_review"
    assert candidate.pack_content["status"] == "pending_review"
    assert any(change["issue"] == "duplicate_ratio_high" for change in candidate.changes)


def test_training_executed_is_false_in_recommendation(tmp_path):
    base_pack = json.loads(
        Path("configs/behavior_packs/fps_mock_v1.example.json").read_text(encoding="utf-8")
    )
    result = BehaviorLearningResult(
        run_id="run_001",
        game_type="fps",
        old_behavior_pack_id="fps_mock_v1",
        metrics=BehaviorMetrics(valid_total=10),
        issues=[],
        recommendations=[],
        should_generate_candidate=True,
        candidate_pack_id=None,
        review_status="pending_review",
    )

    candidate, recommendation = RecommendationEngine().generate_candidate(result, base_pack)

    assert recommendation["training_executed"] is False
    assert candidate.pack_content["training_enabled"] is False
