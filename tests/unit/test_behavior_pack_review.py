from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.common.behavior_learning.recommendation import (
    BehaviorPackCandidate,
)
from ai_screenshot_platform.common.behavior_learning.review import BehaviorReviewManager


def make_candidate() -> BehaviorPackCandidate:
    return BehaviorPackCandidate(
        candidate_pack_id="fps_mock_v2_candidate",
        base_pack_id="fps_mock_v1",
        game_type="fps",
        version="2.0",
        status="pending_review",
        created_from_run_id="run_001",
        created_at="2026-01-01T00:00:00Z",
        rollback_target="fps_mock_v1",
        changes=[],
        pack_content={"pack_id": "fps_mock_v2_candidate", "status": "pending_review"},
    )


def test_pending_rejected_and_approved_enable_rules(tmp_path):
    manager = BehaviorReviewManager(tmp_path)
    candidate = make_candidate()

    assert manager.can_enable(candidate) is False

    rejected = manager.reject_candidate(candidate, reviewer="qa", reason="too risky")
    assert rejected.enabled is False
    assert manager.can_enable(candidate.with_status("rejected")) is False

    approved = manager.approve_candidate(candidate, reviewer="qa", reason="looks good")
    assert approved.enabled is True
    assert manager.can_enable(candidate.with_status("approved")) is True
    assert (tmp_path / "review_record.jsonl").exists()


def test_rollback_records_target(tmp_path):
    manager = BehaviorReviewManager(tmp_path)
    decision = manager.rollback_to(
        candidate_pack_id="fps_mock_v2_candidate",
        reviewer="qa",
        reason="regression",
        rollback_target="fps_mock_v1",
    )

    assert decision.decision == "rollback"
    assert decision.rollback_target == "fps_mock_v1"
    assert decision.enabled is True
    assert (tmp_path / "rollback_record.jsonl").exists()
