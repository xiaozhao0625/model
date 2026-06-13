from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.behavior_learning.inputs import (
    BehaviorLearningInput,
    BehaviorLearningInputReader,
    BehaviorLearningInputError,
)


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
                "high_count": 3,
                "rejected_count": 1,
                "valid_total": 3,
            }
        ),
        encoding="utf-8",
    )
    write_jsonl(
        run_dir / "meta.jsonl",
        [
            {"image_id": "1", "bucket": "high", "valid": True, "content_hash": "a"},
            {"image_id": "2", "bucket": "high", "valid": True, "content_hash": "b"},
            {"image_id": "3", "bucket": "high", "valid": False, "reject_reason": "duplicate_content_hash"},
        ],
    )
    write_jsonl(
        run_dir / "run.log",
        [
            {"event": "image_saved", "status": "running"},
            {"event": "duplicate_rejected", "status": "running"},
            {"event": "capture_completed", "status": "capture_completed"},
        ],
    )
    write_jsonl(
        run_dir / "behavior_actions.jsonl",
        [
            {"action_id": "move", "action_type": "move", "bucket": "high", "skipped": False, "risk_flags": []},
            {"action_id": "hint", "action_type": "capture_hint", "bucket": "high", "skipped": False, "risk_flags": []},
        ],
    )
    return run_dir


def test_behavior_learning_input_reader_reads_run_artifacts(tmp_path):
    run_dir = make_run_dir(tmp_path)
    learning_input = BehaviorLearningInput(
        app_id="app",
        run_id="run",
        game_type="fps",
        behavior_pack_id="fps_mock_v1",
        run_dir=run_dir,
    )

    snapshot = BehaviorLearningInputReader(learning_input).read()

    assert snapshot.summary["valid_total"] == 3
    assert len(snapshot.meta_rows) == 3
    assert len(snapshot.run_events) == 3
    assert len(snapshot.behavior_actions) == 2


def test_missing_behavior_actions_can_degrade_to_empty_when_allowed(tmp_path):
    run_dir = make_run_dir(tmp_path)
    (run_dir / "behavior_actions.jsonl").unlink()
    learning_input = BehaviorLearningInput(
        app_id="app",
        run_id="run",
        game_type="fps",
        behavior_pack_id="fps_mock_v1",
        run_dir=run_dir,
    )

    snapshot = BehaviorLearningInputReader(
        learning_input,
        allow_missing_behavior_actions=True,
    ).read()

    assert snapshot.behavior_actions == []


def test_missing_behavior_actions_raises_clear_error_by_default(tmp_path):
    run_dir = make_run_dir(tmp_path)
    (run_dir / "behavior_actions.jsonl").unlink()
    learning_input = BehaviorLearningInput(
        app_id="app",
        run_id="run",
        game_type="fps",
        behavior_pack_id="fps_mock_v1",
        run_dir=run_dir,
    )

    with pytest.raises(BehaviorLearningInputError, match="behavior_actions.jsonl"):
        BehaviorLearningInputReader(learning_input).read()
