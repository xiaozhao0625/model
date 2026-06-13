from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.behavior_learning.analyzer import (  # noqa: E402
    BehaviorLearningEngine,
)
from ai_screenshot_platform.common.behavior_learning.inputs import (  # noqa: E402
    BehaviorLearningInput,
)
from ai_screenshot_platform.common.behavior_learning.review import (  # noqa: E402
    BehaviorReviewManager,
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _prepare_source_run(run_dir: Path) -> None:
    _write_json(
        run_dir / "summary.json",
        {
            "app_id": "demo_game",
            "run_id": "demo_p12_run",
            "fixed_count": 0,
            "low_count": 0,
            "high_count": 8,
            "rejected_count": 4,
            "valid_total": 8,
        },
    )
    _write_jsonl(
        run_dir / "meta.jsonl",
        [
            {
                "image_id": f"img_{index}",
                "bucket": "high",
                "valid": index < 8,
                "reject_reason": None if index < 8 else "duplicate_content_hash",
            }
            for index in range(12)
        ],
    )
    _write_jsonl(
        run_dir / "run.log",
        [
            {"event": "session_started", "status": "running", "details": {}},
            {
                "event": "duplicate_rejected",
                "status": "running",
                "details": {"reason": "duplicate_content_hash"},
            },
            {
                "event": "failed_low_yield",
                "status": "failed_low_yield",
                "details": {"reason": "manual_seed_still_below_target"},
            },
        ],
    )
    _write_jsonl(
        run_dir / "behavior_actions.jsonl",
        [
            {
                "action_id": "move_1",
                "action_type": "move",
                "bucket": "high",
                "skipped": False,
                "risk_flags": [],
                "result": "ok",
            },
            {
                "action_id": "camera_1",
                "action_type": "camera",
                "bucket": "high",
                "skipped": True,
                "risk_flags": [],
                "result": "stuck",
            },
            {
                "action_id": "capture_1",
                "action_type": "capture_hint",
                "bucket": "high",
                "skipped": False,
                "risk_flags": [],
                "result": "saved",
            },
            {
                "action_id": "death_recovery",
                "action_type": "recovery",
                "bucket": "high",
                "skipped": False,
                "risk_flags": [],
                "result": "death",
            },
        ],
    )
    _write_jsonl(
        run_dir / "manual_seed_record.jsonl",
        [
            {
                "event": "manual_seed_requested",
                "status": "needs_manual_seed",
                "reason": "max_auto_retries_exhausted",
            }
        ],
    )


def main() -> None:
    source_run_dir = REPO_ROOT / "runs" / "dev_p12_smoke" / "source_run"
    output_root = REPO_ROOT / "runs" / "dev_p12_smoke" / "behavior_learning"
    _prepare_source_run(source_run_dir)

    engine = BehaviorLearningEngine(
        output_root=output_root,
        base_pack_path=REPO_ROOT / "configs" / "behavior_packs" / "fps_mock_v1.example.json",
    )
    output = engine.run(
        BehaviorLearningInput(
            app_id="demo_game",
            run_id="demo_p12_run",
            game_type="fps",
            behavior_pack_id="fps_mock_v1",
            run_dir=source_run_dir,
        )
    )

    review_manager = BehaviorReviewManager(output.output_dir)
    approved = review_manager.approve_candidate(
        output.candidate,
        reviewer="tester",
        note="dry-run approval check",
    )
    rollback = review_manager.rollback_to(
        candidate_pack_id=output.candidate.candidate_pack_id,
        reviewer="tester",
        note="dry-run rollback check",
        rollback_target=output.candidate.rollback_target,
    )

    summary = {
        "run_id": "demo_p12_run",
        "old_behavior_pack_id": output.result.old_behavior_pack_id,
        "candidate_pack_id": output.candidate.candidate_pack_id,
        "metrics_path": str(output.output_dir / "metrics.json"),
        "analysis_path": str(output.output_dir / "analysis.json"),
        "recommendation_path": str(output.output_dir / "recommendation.json"),
        "candidate_pack_path": str(output.output_dir / "candidate_pack.json"),
        "review_status": approved.status,
        "approved_enabled": review_manager.can_enable(approved),
        "rollback_target": rollback.rollback_target,
        "training_executed": output.training_executed,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
