import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.behavior.contracts import (
    BehaviorAction,
    BehaviorActionType,
    BehaviorPack,
    BehaviorPackError,
    GameType,
)
from ai_screenshot_platform.common.behavior.loader import BehaviorPackLoader
from ai_screenshot_platform.common.behavior.mock_runner import MockBehaviorRunner
from ai_screenshot_platform.common.behavior.safety import BehaviorSafetyGate
from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FPS_PACK = REPO_ROOT / "configs" / "behavior_packs" / "fps_mock_v1.example.json"
MOBA_PACK = REPO_ROOT / "configs" / "behavior_packs" / "moba_mock_v1.example.json"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_session(tmp_path, target_min=3):
    return LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="demo_game",
            run_id="run_001",
            target_min=target_min,
        )
    )


def test_fps_example_behavior_pack_can_load():
    pack = BehaviorPackLoader.load(FPS_PACK)

    assert pack.pack_id == "fps_mock_v1"
    assert pack.game_type == GameType.FPS
    assert pack.capture_bucket == Bucket.HIGH
    assert pack.record_then_extract is True
    assert {action.action_type for action in pack.actions}.issuperset(
        {
            BehaviorActionType.MOVE,
            BehaviorActionType.CAMERA,
            BehaviorActionType.COMBAT,
            BehaviorActionType.RECOVERY,
            BehaviorActionType.CAPTURE_HINT,
        }
    )


def test_moba_example_behavior_pack_can_load():
    pack = BehaviorPackLoader.load(MOBA_PACK)

    assert pack.pack_id == "moba_mock_v1"
    assert pack.game_type == GameType.MOBA
    assert pack.capture_bucket in {Bucket.LOW, Bucket.HIGH}
    assert {action.action_type for action in pack.actions}.issuperset(
        {
            BehaviorActionType.MOVE,
            BehaviorActionType.CAMERA,
            BehaviorActionType.COMBAT,
            BehaviorActionType.UI,
            BehaviorActionType.RECOVERY,
            BehaviorActionType.CAPTURE_HINT,
        }
    )


def test_behavior_pack_missing_required_field_fails(tmp_path):
    invalid_path = tmp_path / "invalid_pack.json"
    invalid_path.write_text(
        json.dumps(
            {
                "pack_id": "invalid",
                "game_type": "fps",
                "version": "1.0",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BehaviorPackError, match="missing required fields"):
        BehaviorPackLoader.load(invalid_path)


def test_forbidden_context_is_blocked_by_safety_gate():
    pack = BehaviorPack(
        pack_id="safe_pack",
        game_type=GameType.FPS,
        version="1.0",
        status="example",
        allowed_context=["match"],
        forbidden_context=["checkout"],
        capture_bucket=Bucket.HIGH,
        record_then_extract=True,
        actions=[],
    )
    action = BehaviorAction(
        action_id="move_1",
        action_type=BehaviorActionType.MOVE,
        description="move",
        duration_ms=100,
        bucket=Bucket.HIGH,
        risk_flags=[],
        params={},
    )

    decision = BehaviorSafetyGate().validate(pack, action, context=["main menu", "checkout"])

    assert decision.blocked is True
    assert decision.action_type == BehaviorActionType.REQUEST_MANUAL


@pytest.mark.parametrize("risk_flag", ["captcha", "payment", "send_chat"])
def test_forbidden_risk_action_is_blocked(risk_flag):
    pack = BehaviorPack(
        pack_id="risky_pack",
        game_type=GameType.FPS,
        version="1.0",
        status="example",
        allowed_context=[],
        forbidden_context=[],
        capture_bucket=Bucket.HIGH,
        record_then_extract=True,
        actions=[],
    )
    action = BehaviorAction(
        action_id="risk_1",
        action_type=BehaviorActionType.UI,
        description="risky ui",
        duration_ms=100,
        bucket=Bucket.HIGH,
        risk_flags=[risk_flag],
        params={},
    )

    decision = BehaviorSafetyGate().validate(pack, action, context=[])

    assert decision.blocked is True
    assert decision.action_type in {
        BehaviorActionType.REQUEST_MANUAL,
        BehaviorActionType.ABORT,
    }


def test_safe_action_passes_safety_gate():
    pack = BehaviorPack(
        pack_id="safe_pack",
        game_type=GameType.FPS,
        version="1.0",
        status="example",
        allowed_context=[],
        forbidden_context=["shop"],
        capture_bucket=Bucket.HIGH,
        record_then_extract=True,
        actions=[],
    )
    action = BehaviorAction(
        action_id="move_1",
        action_type=BehaviorActionType.MOVE,
        description="safe movement",
        duration_ms=100,
        bucket=Bucket.HIGH,
        risk_flags=[],
        params={},
    )

    decision = BehaviorSafetyGate().validate(pack, action, context=["combat"])

    assert decision.blocked is False
    assert decision.action_type == BehaviorActionType.MOVE


def test_mock_behavior_runner_does_not_execute_real_actions(tmp_path):
    pack = BehaviorPackLoader.load(FPS_PACK)
    session = make_session(tmp_path)
    session.start()

    result = MockBehaviorRunner(pack, session).run(context=["match"])

    assert result.real_actions_executed is False


def test_mock_behavior_runner_writes_behavior_actions_jsonl(tmp_path):
    pack = BehaviorPackLoader.load(FPS_PACK)
    session = make_session(tmp_path)
    session.start()

    result = MockBehaviorRunner(pack, session).run(context=["match"])
    events = load_jsonl(result.actions_log_path)

    assert result.actions_log_path.is_file()
    assert events
    assert {
        "timestamp",
        "app_id",
        "run_id",
        "behavior_pack_id",
        "action_id",
        "action_type",
        "bucket",
        "skipped",
        "risk_flags",
        "result",
    }.issubset(events[0])


def test_mock_behavior_runner_uses_high_bucket_for_mock_images(tmp_path):
    pack = BehaviorPackLoader.load(FPS_PACK)
    session = make_session(tmp_path)
    session.start()

    result = MockBehaviorRunner(pack, session).run(context=["match"])

    assert result.high_count >= 1
    assert result.low_count == 0


def test_mock_behavior_runner_can_enter_capture_completed_with_small_target(tmp_path):
    pack = BehaviorPackLoader.load(FPS_PACK)
    session = make_session(tmp_path, target_min=3)
    session.start()

    result = MockBehaviorRunner(pack, session).run(context=["match"])

    assert result.status == RunStatus.CAPTURE_COMPLETED
    assert result.valid_total >= 3


def test_mock_behavior_runner_does_not_generate_upload_manifest(tmp_path):
    pack = BehaviorPackLoader.load(FPS_PACK)
    session = make_session(tmp_path, target_min=3)
    session.start()

    result = MockBehaviorRunner(pack, session).run(context=["match"])

    assert not (result.run_dir / "upload_manifest.json").exists()


def test_mock_behavior_runner_does_not_enter_completed(tmp_path):
    pack = BehaviorPackLoader.load(FPS_PACK)
    session = make_session(tmp_path, target_min=3)
    session.start()

    result = MockBehaviorRunner(pack, session).run(context=["match"])

    assert result.status != RunStatus.COMPLETED
