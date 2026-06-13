from __future__ import annotations

import json
from pathlib import Path

from ai_screenshot_platform.common.behavior_learning.analyzer import BehaviorLearningEngine
from ai_screenshot_platform.common.behavior_learning.inputs import BehaviorLearningInput
from ai_screenshot_platform.common.behavior_learning.review import BehaviorReviewManager


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def make_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "runs" / "app" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "app_id": "app",
                "run_id": "run",
                "fixed_count": 0,
                "low_count": 0,
                "high_count": 6,
                "rejected_count": 4,
                "valid_total": 6,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    write_jsonl(
        run_dir / "meta.jsonl",
        [{"valid": True, "bucket": "high", "content_hash": str(index)} for index in range(6)]
        + [{"valid": False, "reject_reason": "duplicate_content_hash"} for _ in range(4)],
    )
    write_jsonl(
        run_dir / "run.log",
        [
            {"event": "manual_seed_requested"},
            {"event": "duplicate_rejected"},
            {"event": "failed_low_yield"},
        ],
    )
    write_jsonl(
        run_dir / "behavior_actions.jsonl",
        [
            {"action_id": "move", "action_type": "move", "bucket": "high", "skipped": False, "risk_flags": []},
            {"action_id": "camera", "action_type": "camera", "bucket": "high", "skipped": False, "risk_flags": []},
            {"action_id": "stuck", "action_type": "recovery", "bucket": "high", "skipped": True, "risk_flags": ["stuck"]},
        ],
    )
    return run_dir


def test_behavior_learning_flow_writes_outputs_without_mutating_source(tmp_path):
    run_dir = make_run_dir(tmp_path)
    original_summary = (run_dir / "summary.json").read_text(encoding="utf-8")
    original_meta = (run_dir / "meta.jsonl").read_text(encoding="utf-8")
    original_run_log = (run_dir / "run.log").read_text(encoding="utf-8")
    output_root = tmp_path / "behavior_learning"

    output = BehaviorLearningEngine(
        output_root=output_root,
        base_pack_path="configs/behavior_packs/fps_mock_v1.example.json",
    ).run(
        BehaviorLearningInput(
            app_id="app",
            run_id="run",
            game_type="fps",
            behavior_pack_id="fps_mock_v1",
            run_dir=run_dir,
        )
    )

    assert output.metrics_path.exists()
    assert output.analysis_path.exists()
    assert output.recommendation_path.exists()
    assert output.candidate_pack_path.exists()
    assert json.loads(output.candidate_pack_path.read_text(encoding="utf-8"))["status"] == "pending_review"
    assert (run_dir / "summary.json").read_text(encoding="utf-8") == original_summary
    assert (run_dir / "meta.jsonl").read_text(encoding="utf-8") == original_meta
    assert (run_dir / "run.log").read_text(encoding="utf-8") == original_run_log

    review = BehaviorReviewManager(output.output_dir)
    approved = review.approve_candidate(output.candidate, reviewer="qa", reason="dry run")
    rollback = review.rollback_to(
        output.candidate.candidate_pack_id,
        reviewer="qa",
        reason="rollback simulation",
        rollback_target=output.candidate.rollback_target,
    )

    assert approved.enabled is True
    assert rollback.rollback_target == "fps_mock_v1"
    assert output.training_executed is False
