from pathlib import Path
import json

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.worker.behavior_worker import BehaviorWorkerAgent
from ai_screenshot_platform.common.worker.contracts import (
    WorkerCapability,
    WorkerProfile,
    WorkerState,
    WorkerTask,
    WorkerType,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FPS_PACK = REPO_ROOT / "configs" / "behavior_packs" / "fps_mock_v1.example.json"


def make_pc_game_profile(capabilities=None):
    return WorkerProfile(
        worker_id="pc-game-1",
        machine_name="test-machine",
        worker_type=WorkerType.PC_GAME,
        gpu_name="mock-gpu",
        capabilities=set(
            capabilities
            or {
                WorkerCapability.CAPTURE_HIGH,
                WorkerCapability.BEHAVIOR_PACK,
                WorkerCapability.OBS_CAPTURE,
                WorkerCapability.FFMPEG_EXTRACT,
            }
        ),
        state=WorkerState.IDLE,
        current_run_id=None,
    )


def make_task(tmp_path, behavior_pack_path=FPS_PACK, context=None):
    return WorkerTask(
        app_id="demo_game",
        run_id="run_001",
        app_type="pc_game",
        platform="windows",
        target_min=3,
        target_max=5000,
        bucket="high",
        root_dir=tmp_path,
        behavior_pack_path=behavior_pack_path,
        behavior_pack_id="fps_mock_v1",
        context=context or ["match"],
    )


def test_pc_game_worker_profile_contains_high_behavior_obs_ffmpeg_capabilities():
    profile = make_pc_game_profile()

    assert WorkerCapability.CAPTURE_HIGH in profile.capabilities
    assert WorkerCapability.BEHAVIOR_PACK in profile.capabilities
    assert WorkerCapability.OBS_CAPTURE in profile.capabilities
    assert WorkerCapability.FFMPEG_EXTRACT in profile.capabilities


def test_behavior_worker_can_load_fps_mock_pack(tmp_path):
    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(make_task(tmp_path))

    assert result.behavior_pack_id == "fps_mock_v1"
    assert result.error is None


def test_behavior_worker_enters_capture_completed_with_target_min_three(tmp_path):
    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(make_task(tmp_path))

    assert result.status == RunStatus.CAPTURE_COMPLETED


def test_behavior_worker_result_valid_total_reaches_target_min(tmp_path):
    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(make_task(tmp_path))

    assert result.valid_total >= 3


def test_behavior_worker_result_has_high_count(tmp_path):
    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(make_task(tmp_path))

    assert result.high_count > 0


def test_behavior_worker_writes_summary_meta_behavior_actions_and_run_log(tmp_path):
    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(make_task(tmp_path))

    assert result.summary_path.is_file()
    assert (result.run_dir / "meta.jsonl").is_file()
    assert result.behavior_actions_path is not None
    assert result.behavior_actions_path.is_file()
    assert (result.run_dir / "run.log").is_file()


def test_behavior_worker_does_not_generate_upload_manifest(tmp_path):
    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(make_task(tmp_path))

    assert not (result.run_dir / "upload_manifest.json").exists()


def test_behavior_worker_status_is_not_completed(tmp_path):
    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(make_task(tmp_path))

    assert result.status != RunStatus.COMPLETED


def test_behavior_worker_returns_error_when_behavior_pack_path_missing(tmp_path):
    task = make_task(tmp_path, behavior_pack_path=None)

    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(task)

    assert result.error is not None
    assert "behavior_pack_path is required" in result.error


def test_behavior_worker_returns_error_when_worker_lacks_behavior_pack_capability(tmp_path):
    profile = make_pc_game_profile(capabilities={WorkerCapability.CAPTURE_HIGH})

    result = BehaviorWorkerAgent(profile).execute(make_task(tmp_path))

    assert result.error is not None
    assert "missing required capabilities" in result.error


def test_forbidden_context_returns_error_and_does_not_capture_complete(tmp_path):
    task = make_task(tmp_path, context=["match", "payment"])

    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(task)

    assert result.error is not None
    assert "blocked forbidden behavior risk" in result.error
    assert result.status != RunStatus.CAPTURE_COMPLETED
    assert result.valid_total == 0


def test_high_risk_action_returns_error_and_does_not_create_valid_images(tmp_path):
    payload = json.loads(FPS_PACK.read_text(encoding="utf-8"))
    payload["actions"][0]["risk_flags"] = ["payment"]
    risky_pack_path = tmp_path / "risky_pack.json"
    risky_pack_path.write_text(json.dumps(payload), encoding="utf-8")
    task = make_task(tmp_path, behavior_pack_path=risky_pack_path)

    result = BehaviorWorkerAgent(make_pc_game_profile()).execute(task)

    assert result.error is not None
    assert "blocked forbidden behavior risk" in result.error
    assert result.status != RunStatus.CAPTURE_COMPLETED
    assert result.valid_total == 0
