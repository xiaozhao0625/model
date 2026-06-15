from __future__ import annotations

import json
from pathlib import Path

from scripts.p14.p14_5_onegame_obs_mvp import (
    DEFAULT_BEHAVIOR,
    DEFAULT_PROFILE,
    DEFAULT_QUALITY,
    OneGameQualityGate,
    read_json,
    write_behavior_actions,
    write_solid_png,
)


def test_onegame_profile_is_single_manual_ready_game():
    profile = read_json(DEFAULT_PROFILE)

    assert profile["schema_version"] == "p14.5-onegame-mvp"
    assert profile["mode"] == "manual_ready"
    assert profile["target_total"] == 100
    assert profile["requires_user_ready"] is True
    assert profile["online_inference"] is False
    assert profile["model_action_control"] is False
    assert profile["automatic_upload"] is False
    assert profile["automatic_cleanup"] is False
    assert set(profile["blocked_actions"]) >= {"login", "chat", "purchase", "matchmaking", "ranked"}


def test_frame_quality_gate_rejects_black_and_exact_duplicate(tmp_path: Path):
    policy = read_json(DEFAULT_QUALITY)
    policy["low_detail_laplacian_var_max"] = -1
    policy["low_entropy_max"] = -1
    gate = OneGameQualityGate(policy)
    first = tmp_path / "first.png"
    duplicate = tmp_path / "duplicate.png"
    black = tmp_path / "black.png"
    write_solid_png(first, 640, 480, 128)
    duplicate.write_bytes(first.read_bytes())
    write_solid_png(black, 640, 480, 0)

    first_result = gate.evaluate("first", first)
    duplicate_result = gate.evaluate("duplicate", duplicate)
    black_result = gate.evaluate("black", black)

    assert first_result.quality_status == "accepted"
    assert duplicate_result.quality_status == "duplicate"
    assert duplicate_result.reject_reason == "duplicate"
    assert black_result.quality_status == "rejected"
    assert black_result.reject_reason == "black_screen"


def test_behavior_pack_writes_dry_run_action_log_without_real_execution(tmp_path: Path):
    behavior = read_json(DEFAULT_BEHAVIOR)
    action_log = write_behavior_actions(tmp_path, behavior, execute_real=False)
    rows = [json.loads(line) for line in action_log.read_text(encoding="utf-8").splitlines()]

    assert rows
    assert all(row["dry_run"] is True for row in rows)
    assert all(row["executed"] is False for row in rows)
    assert not any({"login", "chat", "purchase", "matchmaking", "ranked"} & set(row["risk_flags"]) for row in rows)
